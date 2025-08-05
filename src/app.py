import os
import logging
import threading
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from werkzeug.utils import secure_filename
import tempfile

from src.config import config
from src.models import db, Call, Settings
from src.sip_client import SIPClient
from src.whisper_transcriber import WhisperTranscriber
from src.ollama_client import OllamaClient
from src.tts_engines import TTSManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app(config_name='default'):
    """Application factory"""
    import os
    # Get the absolute path to templates and static folders
    # In Docker, the working directory is /app, and templates are at /app/templates
    base_dir = os.getcwd()
    template_dir = os.path.join(base_dir, 'templates')
    static_dir = os.path.join(base_dir, 'static')
    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    
    # Create database tables
    with app.app_context():
        db.create_all()
        # Ensure settings exist
        Settings.get_settings()
    
    # Initialize components
    app.sip_client = None
    app.whisper_transcriber = None
    app.ollama_client = None
    app.tts_manager = None
    
    # Initialize components in background
    def init_components():
        with app.app_context():
            try:
                # Initialize Whisper transcriber
                settings = Settings.get_settings()
                app.whisper_transcriber = WhisperTranscriber(
                    model_size=settings.whisper_model_size,
                    device=settings.whisper_device
                )
                logger.info("Whisper transcriber initialized")
                
                # Initialize Ollama client
                app.ollama_client = OllamaClient(settings.ollama_url)
                logger.info("Ollama client initialized")
                
                # Initialize TTS manager
                app.tts_manager = TTSManager()
                logger.info("TTS manager initialized")
                
                # Initialize SIP client
                app.sip_client = SIPClient(
                    domain=settings.sip_domain,
                    username=settings.sip_username,
                    password=settings.sip_password,
                    port=settings.sip_port
                )
                
                # Set SIP callbacks
                app.sip_client.set_callbacks(
                    on_incoming_call=app._handle_incoming_call,
                    on_call_transcript=app._handle_call_transcript,
                    on_call_end=app._handle_call_end
                )
                
                # Register with SIP server
                if app.sip_client.register():
                    logger.info("SIP client registered successfully")
                else:
                    logger.error("SIP registration failed")
                
            except Exception as e:
                logger.error(f"Failed to initialize components: {e}")
    
    # Start initialization in background
    init_thread = threading.Thread(target=init_components)
    init_thread.daemon = True
    init_thread.start()
    
    # Setup Flask-Admin
    admin = Admin(app, name='CallBot Admin', template_mode='bootstrap3')
    admin.add_view(ModelView(Call, db.session))
    admin.add_view(ModelView(Settings, db.session))
    
    @app.route('/')
    def index():
        """Home page"""
        return render_template('index.html')
    
    @app.route('/conversations')
    def conversations():
        """Conversations page - list all calls"""
        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '')
        
        # Build query
        query = Call.query
        
        if search:
            query = query.filter(
                db.or_(
                    Call.transcript.contains(search),
                    Call.ai_response.contains(search),
                    Call.caller_id.contains(search)
                )
            )
        
        # Order by timestamp descending
        query = query.order_by(Call.timestamp.desc())
        
        # Paginate
        calls = query.paginate(
            page=page, per_page=20, error_out=False
        )
        
        return render_template('conversations.html', calls=calls, search=search)
    
    @app.route('/settings', methods=['GET', 'POST'])
    def settings():
        """Settings page"""
        settings_obj = Settings.get_settings()
        
        if request.method == 'POST':
            try:
                # Update settings
                settings_obj.ollama_url = request.form['ollama_url']
                settings_obj.ollama_model = request.form['ollama_model']
                settings_obj.tts_engine = request.form['tts_engine']
                settings_obj.tts_voice = request.form['tts_voice']
                settings_obj.sip_domain = request.form['sip_domain']
                settings_obj.sip_username = request.form['sip_username']
                settings_obj.sip_password = request.form['sip_password']
                settings_obj.sip_port = int(request.form['sip_port'])
                settings_obj.whisper_model_size = request.form['whisper_model_size']
                settings_obj.whisper_device = request.form['whisper_device']
                
                db.session.commit()
                flash('Settings saved successfully!', 'success')
                
                # Reinitialize components with new settings
                def reinit_components():
                    with app.app_context():
                        try:
                            # Reinitialize components with new settings
                            app.whisper_transcriber = WhisperTranscriber(
                                model_size=settings_obj.whisper_model_size,
                                device=settings_obj.whisper_device
                            )
                            
                            app.ollama_client = OllamaClient(settings_obj.ollama_url)
                            
                            if app.sip_client:
                                app.sip_client.shutdown()
                            
                            app.sip_client = SIPClient(
                                domain=settings_obj.sip_domain,
                                username=settings_obj.sip_username,
                                password=settings_obj.sip_password,
                                port=settings_obj.sip_port
                            )
                            
                            app.sip_client.set_callbacks(
                                on_incoming_call=app._handle_incoming_call,
                                on_call_transcript=app._handle_call_transcript,
                                on_call_end=app._handle_call_end
                            )
                            
                            if app.sip_client.register():
                                logger.info("SIP client re-registered successfully")
                            
                        except Exception as e:
                            logger.error(f"Failed to reinitialize components: {e}")
                
                reinit_thread = threading.Thread(target=reinit_components)
                reinit_thread.daemon = True
                reinit_thread.start()
                
                return redirect(url_for('settings'))
                
            except Exception as e:
                flash(f'Error saving settings: {e}', 'error')
        
        # Get available models and voices
        ollama_models = []
        if app.ollama_client:
            ollama_models = app.ollama_client.list_models() or []
        
        tts_engines = {}
        if app.tts_manager:
            tts_engines = app.tts_manager.get_available_engines()
        
        return render_template('settings.html', 
                            settings=settings_obj,
                            ollama_models=ollama_models,
                            tts_engines=tts_engines)
    
    @app.route('/api/calls')
    def api_calls():
        """API endpoint to get calls"""
        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '')
        
        query = Call.query
        
        if search:
            query = query.filter(
                db.or_(
                    Call.transcript.contains(search),
                    Call.ai_response.contains(search),
                    Call.caller_id.contains(search)
                )
            )
        
        calls = query.order_by(Call.timestamp.desc()).paginate(
            page=page, per_page=20, error_out=False
        )
        
        return jsonify({
            'calls': [call.to_dict() for call in calls.items],
            'total': calls.total,
            'pages': calls.pages,
            'current_page': calls.page
        })
    
    @app.route('/api/active_calls')
    def api_active_calls():
        """API endpoint to get active calls"""
        if app.sip_client:
            return jsonify(app.sip_client.get_active_calls())
        return jsonify({})
    
    @app.route('/api/test_ollama')
    def api_test_ollama():
        """Test Ollama connection"""
        if app.ollama_client:
            status = app.ollama_client.test_connection()
            return jsonify(status)
        return jsonify({'connected': False, 'error': 'Ollama client not initialized'})
    
    @app.route('/api/audio/<int:call_id>')
    def api_audio(call_id):
        """Serve audio file for a call"""
        call = Call.query.get_or_404(call_id)
        
        if call.audio_filename and os.path.exists(call.audio_filename):
            return send_file(call.audio_filename, mimetype='audio/wav')
        
        return jsonify({'error': 'Audio file not found'}), 404
    
    # Call handling methods
    def _handle_incoming_call(self, call_id: str, caller_id: str):
        """Handle incoming call"""
        logger.info(f"Handling incoming call {call_id} from {caller_id}")
        
        # Create call record
        call = Call(
            caller_id=caller_id,
            status='in_progress'
        )
        db.session.add(call)
        db.session.commit()
        
        # Store call ID mapping
        if not hasattr(self, '_call_mapping'):
            self._call_mapping = {}
        self._call_mapping[call_id] = call.id
    
    def _handle_call_transcript(self, call_id: str, transcript: str):
        """Handle transcript from call"""
        logger.info(f"Call {call_id} transcript: {transcript}")
        
        # Get call record
        if hasattr(self, '_call_mapping') and call_id in self._call_mapping:
            call_id_db = self._call_mapping[call_id]
            call = Call.query.get(call_id_db)
            
            if call:
                # Update transcript
                if call.transcript:
                    call.transcript += " " + transcript
                else:
                    call.transcript = transcript
                
                db.session.commit()
                
                # Generate AI response
                self._generate_ai_response(call, transcript)
    
    def _handle_call_end(self, call_id: str):
        """Handle call end"""
        logger.info(f"Call {call_id} ended")
        
        # Get call record
        if hasattr(self, '_call_mapping') and call_id in self._call_mapping:
            call_id_db = self._call_mapping[call_id]
            call = Call.query.get(call_id_db)
            
            if call:
                call.status = 'completed'
                call.duration = int((datetime.utcnow() - call.timestamp).total_seconds())
                db.session.commit()
                
                # Clean up mapping
                del self._call_mapping[call_id]
    
    def _generate_ai_response(self, call: Call, transcript: str):
        """Generate AI response for call"""
        try:
            if not app.ollama_client:
                logger.error("Ollama client not available")
                return
            
            settings = Settings.get_settings()
            
            # Generate AI response
            ai_response = app.ollama_client.generate_with_context(
                transcript=transcript,
                model=settings.ollama_model
            )
            
            if ai_response:
                call.ai_response = ai_response
                db.session.commit()
                
                # Generate TTS audio
                self._generate_tts_audio(call, ai_response)
                
        except Exception as e:
            logger.error(f"Failed to generate AI response: {e}")
    
    def _generate_tts_audio(self, call: Call, text: str):
        """Generate TTS audio for call"""
        try:
            if not app.tts_manager:
                logger.error("TTS manager not available")
                return
            
            settings = Settings.get_settings()
            
            # Create audio output directory
            audio_dir = app.config.get('AUDIO_OUTPUT_DIR', 'audio_output')
            os.makedirs(audio_dir, exist_ok=True)
            
            # Generate audio filename
            audio_filename = os.path.join(audio_dir, f"call_{call.id}_{int(time.time())}.wav")
            
            # Generate TTS audio
            success = app.tts_manager.synthesize(
                text=text,
                engine_name=settings.tts_engine,
                voice=settings.tts_voice,
                output_path=audio_filename
            )
            
            if success:
                call.audio_filename = audio_filename
                call.tts_voice = settings.tts_voice
                db.session.commit()
                
                # Play audio to call
                if app.sip_client and hasattr(self, '_call_mapping'):
                    # Find call ID from database ID
                    for sip_call_id, db_call_id in self._call_mapping.items():
                        if db_call_id == call.id:
                            app.sip_client.play_audio(sip_call_id, audio_filename)
                            break
                
                logger.info(f"TTS audio generated: {audio_filename}")
            else:
                logger.error("Failed to generate TTS audio")
                
        except Exception as e:
            logger.error(f"Failed to generate TTS audio: {e}")
    
    return app

def main():
    """Main entry point for the application"""
    app = create_app()
    app.run(
        host=app.config.get('WEB_HOST', '0.0.0.0'),
        port=app.config.get('WEB_PORT', 5000),
        debug=app.config.get('DEBUG', False)
    )

if __name__ == '__main__':
    main() 
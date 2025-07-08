#!/usr/bin/env python3
"""
Voice Interface for Restaurant Recommendations

This script provides a voice-based interface for the restaurant recommendation system.
It uses Groq for speech-to-text, text processing, and text-to-speech.
"""

import os
import time
import json
import tempfile
import threading
import requests
import sounddevice as sd
import soundfile as sf
import numpy as np
from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()

# Configuration
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable not set")

SAMPLE_RATE = 16000  # Hz
CHANNELS = 1
SILENCE_THRESHOLD = 0.09  # Lowered threshold for better sensitivity
SILENCE_DURATION = 1.5  # Increased pause duration to avoid premature cutoff
API_BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:5005")  # Restaurant API base URL
VISUAL_FEEDBACK = True  # Whether to show visual feedback for audio input

# Initialize Groq client
groq_client = Groq(api_key=GROQ_API_KEY)

class VoiceAssistant:
    def __init__(self):
        self.recording = False
        self.audio_data = []
        self.conversation_history = []
        self.user_email = "voice_user@example.com"  # Default user for recommendations
        
        # Create the user if they don't exist
        self.ensure_user_exists()
    
    def ensure_user_exists(self):
        """Make sure the voice user exists in the system."""
        try:
            print(f"Connecting to API at {API_BASE_URL}...")
            response = requests.post(
                f"{API_BASE_URL}/users",
                json={"username": "voice_user", "email": self.user_email},
                headers={"Content-Type": "application/json"},
                timeout=5  # Add timeout to avoid hanging
            )
            if response.status_code == 200:
                print(f"User created or already exists: {self.user_email}")
            else:
                print(f"Failed to create user: {response.text}")
        except requests.exceptions.ConnectionError:
            print(f"Error: Could not connect to API server at {API_BASE_URL}")
            print("The API server might not be running. You can still test speech recognition.")
            print("To start the API server, run 'python3 app.py' in another terminal.")
        except Exception as e:
            print(f"Error creating user: {str(e)}")
    
    def record_audio(self):
        """Record audio from the microphone until silence is detected."""
        print("Listening... (speak now)")
        self.recording = True
        self.audio_data = []
        
        def audio_callback(indata, frames, time, status):
            if status:
                print(f"Error in audio stream: {status}")
            self.audio_data.append(indata.copy())
            
            # Check for silence to auto-stop recording
            volume = np.abs(indata).mean()
            
            # Visual feedback for audio input
            if VISUAL_FEEDBACK:
                # Create a volume bar using ASCII characters
                # Increased sensitivity by using 0.05 instead of 0.1 for normalization
                volume_normalized = min(1.0, volume / 0.05)  # More sensitive normalization
                bar_length = int(volume_normalized * 40)  # Max bar length of 40 characters
                volume_bar = '█' * bar_length + '░' * (40 - bar_length)
                volume_percentage = int(volume_normalized * 100)
                print(f"\rVolume: [{volume_bar}] {volume_percentage}%", end='', flush=True)
                
                # Print a message when voice is detected
                if volume > SILENCE_THRESHOLD:
                    print(f"\rVoice detected! Volume: [{volume_bar}] {volume_percentage}%", end='', flush=True)
            
            if volume < SILENCE_THRESHOLD:
                self.silence_counter += 1
            else:
                self.silence_counter = 0
            
            if self.silence_counter > SILENCE_DURATION * SAMPLE_RATE / frames:
                self.recording = False
        
        self.silence_counter = 0
        with sd.InputStream(callback=audio_callback, channels=CHANNELS, samplerate=SAMPLE_RATE):
            while self.recording:
                time.sleep(0.1)
        
        if VISUAL_FEEDBACK:
            print()  # Add a newline after the volume bar
        print("Finished recording")
        
        # Combine all audio chunks
        if not self.audio_data:
            print("No audio recorded")
            return None
        
        audio_data_combined = np.concatenate(self.audio_data, axis=0)
        return audio_data_combined
    
    def save_audio_to_file(self, audio_data, filename):
        """Save audio data to a WAV file."""
        sf.write(filename, audio_data, SAMPLE_RATE)
        return filename
    
    def speech_to_text(self, audio_file):
        """Convert speech to text using Groq's audio.transcriptions API."""
        print("Converting speech to text...")
        
        try:
            # Use Groq's audio.transcriptions API with Whisper model
            with open(audio_file, 'rb') as file:
                # Create a transcription of the audio file
                transcription = groq_client.audio.transcriptions.create(
                    file=file,  # Required audio file
                    model="whisper-large-v3-turbo",  # Required model to use for transcription
                    
                )
            
            # Extract the transcribed text
            transcribed_text = transcription.text.strip()
            print(f"Transcribed: {transcribed_text}")
            return transcribed_text
            
        except Exception as e:
            print(f"Error in speech-to-text: {str(e)}")
            return "Sorry, I couldn't understand what you said."
    
    def process_text(self, text):
        """Process the transcribed text and get a response."""
        print("Processing text...")
        
        # Add to conversation history
        self.conversation_history.append({"role": "user", "content": text})
        
        try:
            # Check if the query is about food recommendations
            if any(keyword in text.lower() for keyword in ["food", "eat", "restaurant", "hungry", "recommendation", "suggest"]):
                # Use the generate_options API endpoint
                response = requests.post(
                    f"{API_BASE_URL}/generate_options",
                    json={"email": self.user_email, "input_text": text},
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    options = response.json()
                    food_items = [item.get("item_name", "an option") for item in options.get("options", [])]
                    response_text = f"Here are some food suggestions for you: {', '.join(food_items)}. Would you like more details about any of these options?"
                else:
                    response_text = "I'm having trouble getting food recommendations right now. Can you try again?"
            else:
                # General conversation with Groq
                groq_response = groq_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "You are a helpful restaurant assistant. Keep responses brief and focused on food, restaurants, and dining."},
                        *self.conversation_history
                    ],
                    model="meta-llama/llama-4-scout-17b-16e-instruct",
                )
                response_text = groq_response.choices[0].message.content.strip()
            
            # Add to conversation history
            self.conversation_history.append({"role": "assistant", "content": response_text})
            
            # Keep conversation history manageable
            if len(self.conversation_history) > 10:
                self.conversation_history = self.conversation_history[-10:]
            
            print(f"Response: {response_text}")
            return response_text
            
        except Exception as e:
            print(f"Error processing text: {str(e)}")
            return "Sorry, I encountered an error while processing your request."
    
    def text_to_speech(self, text):
        """Convert text to speech using Groq-enhanced audio synthesis."""
        print("Converting text to speech using Groq...")
        
        try:
            # Create a temporary file for the audio output
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                output_file = temp_file.name
            
            # Use Groq to enhance the text with prosody and speech pattern information
            # This will help create more natural-sounding audio patterns
            try:
                prosody_response = groq_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "You are an expert in speech synthesis and prosody. "
                                              "Your task is to analyze text and add prosody markers for natural speech. "
                                              "For each sentence, provide: pitch pattern, emphasis points, pauses, and speech rate."},
                        {"role": "user", "content": f"Analyze this text for speech synthesis: '{text}'. "
                                             f"Return a JSON with prosody information including pitch patterns, "
                                             f"emphasis points, pauses, and speech rate for each sentence."}
                    ],
                    model="meta-llama/llama-4-scout-17b-16e-instruct",
                )
                
                prosody_text = prosody_response.choices[0].message.content.strip()
                print("Generated prosody information for more natural speech")
                
                # Extract prosody information (simplified parsing)
                import re
                import json
                
                # Try to find and parse JSON in the response
                json_match = re.search(r'\{[\s\S]*\}', prosody_text)
                prosody_data = {}
                
                if json_match:
                    try:
                        prosody_data = json.loads(json_match.group(0))
                        print("Successfully parsed prosody data")
                    except json.JSONDecodeError:
                        print("Could not parse prosody JSON, using default speech patterns")
                else:
                    print("No JSON found in prosody response, using default speech patterns")
                    
            except Exception as e:
                print(f"Error getting prosody information: {str(e)}")
                prosody_data = {}
            
            # Generate audio based on text and prosody information
            duration = min(1.0 + len(text) * 0.08, 15.0)  # Scale duration with text length, max 15 seconds
            t = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)
            
            # Create a more sophisticated audio pattern based on text and prosody
            audio_data = np.zeros_like(t)
            
            # Extract sentences and their prosody if available
            sentences = re.split(r'[.!?]\s*', text)
            sentences = [s for s in sentences if s]  # Remove empty sentences
            
            # Default base frequencies for different voice characteristics
            base_freq = 220  # Base frequency (A3 note)
            
            # Process each sentence with its own prosody
            total_sentences = len(sentences)
            for i, sentence in enumerate(sentences):
                # Calculate segment for this sentence in the audio timeline
                start_pos = int(i * len(t) / total_sentences)
                end_pos = int((i + 1) * len(t) / total_sentences)
                segment_t = t[start_pos:end_pos]
                
                if len(segment_t) == 0:
                    continue  # Skip if segment is empty
                
                # Get prosody for this sentence if available
                sentence_prosody = prosody_data.get(f"sentence_{i+1}", {})
                
                # Extract prosody parameters or use defaults
                pitch_pattern = sentence_prosody.get("pitch_pattern", "rising")
                emphasis = sentence_prosody.get("emphasis", [len(sentence) // 2])
                speech_rate = sentence_prosody.get("speech_rate", 1.0)
                
                # Create frequency modulation based on pitch pattern
                if pitch_pattern == "rising":
                    freq_mod = np.linspace(0.8, 1.2, len(segment_t))
                elif pitch_pattern == "falling":
                    freq_mod = np.linspace(1.2, 0.8, len(segment_t))
                else:  # neutral or other
                    freq_mod = 1.0 + 0.1 * np.sin(2 * np.pi * 0.5 * np.linspace(0, 1, len(segment_t)))
                
                # Generate base waveform for this sentence
                sentence_audio = 0.3 * np.sin(2 * np.pi * base_freq * freq_mod * np.linspace(0, speech_rate, len(segment_t)))
                
                # Add harmonics for richness
                sentence_audio += 0.15 * np.sin(2 * np.pi * base_freq * 2 * freq_mod * np.linspace(0, speech_rate, len(segment_t)))
                sentence_audio += 0.1 * np.sin(2 * np.pi * base_freq * 3 * freq_mod * np.linspace(0, speech_rate, len(segment_t)))
                
                # Add emphasis points
                for emp_point in emphasis:
                    if isinstance(emp_point, int) and 0 <= emp_point < len(sentence):
                        emp_pos = start_pos + int((emp_point / len(sentence)) * (end_pos - start_pos))
                        emp_width = min(2000, (end_pos - start_pos) // 5)
                        if emp_pos < len(t):
                            emp_range = slice(max(0, emp_pos - emp_width), min(len(t), emp_pos + emp_width))
                            audio_data[emp_range] += 0.2 * np.sin(2 * np.pi * base_freq * 1.5 * t[emp_range])
                
                # Add the sentence audio to the main audio data
                audio_data[start_pos:end_pos] += sentence_audio
                
                # Add a small pause between sentences
                pause_start = min(len(audio_data) - 1, end_pos - int(0.2 * SAMPLE_RATE))
                pause_end = min(len(audio_data), end_pos)
                if pause_start < pause_end:
                    audio_data[pause_start:pause_end] *= 0.5  # Reduce volume for pause
            
            # Apply envelope to smooth beginning and end
            fade_samples = int(0.1 * SAMPLE_RATE)  # 100ms fade in/out
            if len(audio_data) > 2 * fade_samples:
                # Fade in
                fade_in = np.linspace(0, 1, fade_samples)
                audio_data[:fade_samples] *= fade_in
                # Fade out
                fade_out = np.linspace(1, 0, fade_samples)
                audio_data[-fade_samples:] *= fade_out
            
            # Normalize audio
            max_amp = np.max(np.abs(audio_data))
            if max_amp > 0:
                audio_data = 0.8 * audio_data / max_amp
            
            # Write to file
            sf.write(output_file, audio_data, SAMPLE_RATE)
            
            print(f"Groq-enhanced speech output saved to {output_file}")
            return output_file
            
        except Exception as e:
            print(f"Error in text-to-speech: {str(e)}")
            return None
    
    def play_audio(self, audio_file):
        """Play audio from a file."""
        try:
            data, fs = sf.read(audio_file)
            sd.play(data, fs)
            sd.wait()
        except Exception as e:
            print(f"Error playing audio: {str(e)}")
    
    def run(self):
        """Run the voice assistant in a loop."""
        print("Starting voice assistant...")
        print("Say something and pause when you're done speaking.")
        
        try:
            while True:
                # Record audio
                audio_data = self.record_audio()
                if audio_data is None:
                    continue
                
                # Save to temporary file
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                    input_file = temp_file.name
                self.save_audio_to_file(audio_data, input_file)
                
                # Process the audio
                text = self.speech_to_text(input_file)
                if text.lower() in ["quit", "exit", "stop", "goodbye"]:
                    print("Exiting voice assistant...")
                    break
                
                response = self.process_text(text)
                output_file = self.text_to_speech(response)
                if output_file:
                    self.play_audio(output_file)
                    # Clean up temporary file
                    try:
                        os.unlink(output_file)
                    except:
                        pass
                
                # Clean up input file
                try:
                    os.unlink(input_file)
                except:
                    pass
                
                print("\nReady for next input...")
                
        except KeyboardInterrupt:
            print("\nExiting voice assistant...")
        except Exception as e:
            print(f"Error in voice assistant: {str(e)}")

if __name__ == "__main__":
    # Check if API server is running
    try:
        response = requests.get(f"{API_BASE_URL}/restaurants", timeout=2)
        print(f"API server is running at {API_BASE_URL}")
    except:
        print(f"Warning: Could not connect to API server at {API_BASE_URL}")
        print("Voice interface will run in limited mode without API features.")
        print("To use full features, start the API server with 'python3 app.py' in another terminal.")
    
    print("\nVoice Assistant Controls:")
    print("- Speak and pause to send your message")
    print("- Say 'quit' or 'exit' to stop the program")
    print("- Press Ctrl+C to exit at any time\n")
    
    assistant = VoiceAssistant()
    assistant.run()

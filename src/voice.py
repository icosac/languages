from TTS.api import TTS

import os
import sys
import contextlib

try:
    import sounddevice as sd
except ImportError:
    raise ImportError("Please install sounddevice to play audio directly.")

from my_logger import logger

@contextlib.contextmanager
def suppress_stdout_stderr():
    with open(os.devnull, 'w') as devnull:
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = devnull, devnull
        try:
            yield
        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr


class audio:
    def __init__(self, model_type = "tts_models/de/thorsten/tacotron2-DDC", use_gpu = False, verbose = False):
        self.model_type = model_type
        self.use_gpu = use_gpu
        self.verbose = verbose
        # Load the German model
        if self.verbose:
            self.model = TTS(model_name=self.model_type, progress_bar=True)
        else:
            with suppress_stdout_stderr():
                self.model = TTS(model_name=self.model_type, progress_bar=True)

        if self.use_gpu:
            logger.debug("Using GPU for TTS")
            self.model.to("cuda")


    def __call__(self, text, immediately = False, file_name = None):
        if self.verbose:
            if file_name is not None:
                self.__generate_wav_file(text, file_name)
            else:
                return self.__speak(text, immediately)
        else:
            with suppress_stdout_stderr():
                if file_name is not None:
                    self.__generate_wav_file(text, file_name)
                else:
                    return self.__speak(text, immediately)
        return None


    def __speak(self, text, immediately):        
        # Synthesize directly to a waveform (returns audio and sample rate)
        audio = self.model.tts(text, speed=1.5, split_sentences=False)

        # Get the sample rate from the model
        sample_rate = self.model.synthesizer.output_sample_rate

        # Play the audio directly
        if immediately:
            sd.play(audio, samplerate=sample_rate)
            sd.wait()

        return audio, sample_rate


    def __generate_wav_file(self, text, file_name):
        assert file_name.endswith(".wav"), "File name must end with .wav"

        # Generate speech
        self.model.tts_to_file(text=text, file_path="file_name")
        

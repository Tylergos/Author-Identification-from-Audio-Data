import librosa
import os
import numpy as np
import pickle
import speech_recognition as sr
import nltk
from sklearn.model_selection import StratifiedKFold
import tensorflow as tf

from Lexicon import Lexicon
from LSTM import LSTM

from keras.datasets import imdb
from keras.utils import pad_sequences

DATASET_PATH = "./SpeakersDataset/50_speakers_audio_data"
PICKLE_AUDIO_FILE_PATH = "./AudioData.txt"
PICKLE_TEXT_FILE_PATH = "./TextData.txt"
SAMPLE_RATE = 11025
CLIP_LENGTH = 661504


def read_and_save_audio(file_name: str = PICKLE_AUDIO_FILE_PATH) -> None:
    speaker_files = dict()
    for speaker in os.listdir(DATASET_PATH):
        audio_files = list()
        for audio_file in os.listdir(DATASET_PATH + "/" + speaker):
            print(audio_file)
            # open and resample the files from ~22Khz to ~11KHz.
            try:
                audio_files.append(librosa.load(DATASET_PATH + "/" + speaker + "/" + audio_file, sr=SAMPLE_RATE))
            except:
                print("File failed to resample: " + audio_file)
        speaker_files[speaker] = audio_files
    pickle_file = open(file_name, "wb")
    pickle.dump(speaker_files, pickle_file)
    pickle_file.close()


def read_saved_audio(file_name: str = PICKLE_AUDIO_FILE_PATH) -> dict[list[str]]:
    file = open(file_name, "rb")
    audio_data = pickle.load(file)
    file.close()
    return audio_data


def speech_to_text(file_name: str = PICKLE_TEXT_FILE_PATH, quick_run: bool = False) -> None:
    r = sr.Recognizer()
    speaker_files = dict()
    for speaker in os.listdir(DATASET_PATH):
        text_files = list()
        for audio_file in os.listdir(DATASET_PATH + "/" + speaker):
            print(audio_file)

            try:
                with sr.AudioFile(DATASET_PATH + "/" + speaker + "/" + audio_file) as source:
                    audio = r.record(source)
                text_files.append(r.recognize_google(audio))

                if quick_run:
                    break
            except LookupError:  # speech is unintelligible
                print("Could not understand audio")
            except: # file is corrupted or has issues
                print("File is corrupted or has issues")
        speaker_files[speaker] = text_files
    pickle_file = open(file_name, "wb")
    pickle.dump(speaker_files, pickle_file)
    pickle_file.close()


def read_saved_text(file_name: str = PICKLE_TEXT_FILE_PATH) -> dict[list[str]]:
    file = open(file_name, "rb")
    text_data = pickle.load(file)
    file.close()
    return text_data


def main():
    # Running these will overwrite current data, ensure that you mean to do so before running it
    # read_and_save_audio()
    # speech_to_text(quick_run=True)

    audio_data = read_saved_audio()
    print(audio_data)
    text_data = read_saved_text()

    lexicon_model = Lexicon(text_data)

    print(lexicon_model.classify(str(text_data["Speaker0033"])))

    x = []
    y = []
    for (author, data) in audio_data.items():
        for clip in data:
            # don't need the sample rate, thus we only take index 0
            x.append(clip[0])
            y.append(int(author[-2::]))

    # We need to pad the clips as they are not all exactly the same length
    x = pad_sequences(x, maxlen=CLIP_LENGTH, dtype=float)
    y = np.array(y)

    kfold = StratifiedKFold(5)

    accuracies = []
    for fold, (train_index, test_index) in enumerate(kfold.split(x, y)):
        train_x = tf.convert_to_tensor(x[train_index])
        train_y = tf.convert_to_tensor(y[train_index])
        test_x = tf.convert_to_tensor(x[test_index])
        test_y = tf.convert_to_tensor(y[test_index])

        lstm_model = LSTM()
        lstm_model.train_model(train_x, train_y, test_x, test_y)
        accuracies.append(lstm_model.evaluate(test_x, test_y))
    print(accuracies)



if __name__ == '__main__':
    main()
import argparse, sys
import random

from my_logger import logger, logging

def help_message(printable = True):
    numbers_s = [
        "null", "eins", "zwei", "drei", "vier", "fünf", "sechs", "sieben", "acht", "neun",
        "zehn", "elf", "zwölf", "dreizehn", "vierzehn", "fünfzehn", "sechzehn", "siebzehn",
        "achtzehn", "neunzehn"
    ]

    help_message = "== 1-20 =======================================================\n"

    for i in range(len(numbers_s)):
        if i % 5 == 4: 
            help_message += f"{i} = {numbers_s[i]}\n"
        else:
            help_message += f"{i} = {numbers_s[i]}\t"

    help_message += "\n== 20,30,40,50,60,70,80,90,100 ===============================\n"

    number_ty = [
        "zwanzig", "dreißig", "vierzig", "fünfzig", "sechzig", "siebzig", "achtzig", "neunzig", "hundert"
    ]

    for i in range(len(number_ty)):
        if i % 2 == 1: 
            help_message += f"{(i + 2)*10} = {number_ty[i]}\n"
        else:
            help_message += f"{(i + 2)*10} = {number_ty[i]}\t"

    print(help_message) 


# All German numbers as strings
numbers = [
    "null", "eins", "zwei", "drei", "vier", "fünf", "sechs", "sieben", "acht", "neun",
    "zehn", "elf", "zwölf", "dreizehn", "vierzehn", "fünfzehn", "sechzehn", "siebzehn", "achtzehn", "neunzehn", 
    "zwanzig", "einundzwanzig", "zweiundzwanzig", "dreiundzwanzig", "vierundzwanzig", "fünfundzwanzig", "sechsundzwanzig", "siebenundzwanzig", "achtundzwanzig", "neunundzwanzig", 
    "dreißig", "einunddreißig", "zweiunddreißig", "dreiunddreißig", "vierunddreißig", "fünfunddreißig", "sechsunddreißig", "siebenunddreißig", "achtunddreißig", "neununddreißig", 
    "vierzig", "einundvierzig", "zweiundvierzig", "dreiundvierzig", "vierundvierzig", "fünfundvierzig", "sechsundvierzig", "siebenundvierzig", "achtundvierzig", "neunundvierzig", 
    "fünfzig", "einundfünfzig", "zweiundfünfzig", "dreiundfünfzig", "vierundfünfzig", "fünfundfünfzig", "sechsundfünfzig", "siebenundfünfzig", "achtundfünfzig", "neunundfünfzig", 
    "sechzig", "einundsechzig", "zweiundsechzig", "dreiundsechzig", "vierundsechzig", "fünfundsechzig", "sechsundsechzig", "siebenundsechzig", "achtundsechzig", "neunundsechzig", 
    "siebzig", "einundsiebzig", "zweiundsiebzig", "dreiundsiebzig", "vierundsiebzig", "fünfundsiebzig", "sechsundsiebzig", "siebenundsiebzig", "achtundsiebzig", "neunundsiebzig", 
    "achtzig", "einundachtzig", "zweiundachtzig", "dreiundachtzig", "vierundachtzig", "fünfundachtzig", "sechsundachtzig", "siebenundachtzig", "achtundachtzig", "neunundachtzig", 
    "neunzig", "einundneunzig", "zweiundneunzig", "dreiundneunzig", "vierundneunzig", "fünfundneunzig", "sechsundneunzig", "siebenundneunzig", "achtundneunzig", "neunundneunzig", 
    "hundert"]


def extract_numbers(n_repetitions):
    """
    Extract numbers from the list.
    """
    return random.sample(range(len(numbers)), n_repetitions)


def print_results(done, correct, counter):
    if counter > 0:
        print("=======================================================")
        print(f"You got {correct} out of {counter} answers.")
        print("=======================================================")

        print("Summary: ")
        for num, answer, correct in done:
            if answer != correct:
                print("X", end=" ")
            else:
                print("V", end=" ")

            print(f"{num} {answer} {correct}")


def main_voice(n_repetitions, use_gpu):
    from voice import audio

    # Create an instance of the audio class
    logger.debug("Loading TTS model...")
    tts = audio(model_type="tts_models/de/thorsten/tacotron2-DDC", use_gpu=use_gpu, verbose=logger.level == logging.DEBUG)
    logger.debug("TTS model loaded.")

    counter = 0
    correct = 0

    done = list()

    test = extract_numbers(n_repetitions)

    for num in test:
        answer = "r"

        logger.debug("Generating audio for number: %d %s", num, numbers[num])

        while answer == "r":
            tts(numbers[num])
            answer = input(f"Write the number in German ('r' to repeat, 'e' to exit): ")
            answer = answer.lower().strip()

        if answer == "e":
            break

        done.append((num, answer, numbers[num]))

        # Check if the answer is correct
        if answer == numbers[num]:
            correct += 1
        counter += 1

    print_results(done, correct, counter)


def main_text(n_repetitions):
    counter = 0
    correct = 0

    done = list()

    test = extract_numbers(n_repetitions)

    for num in test:

        # Print the number and make the user write it in German
        answer = input(f"Write {num} in German ('e' to exit): ")
        answer = answer.lower().strip()

        if answer == "e":
            break

        done.append((num, answer, numbers[num]))

        # Check if the answer is correct
        if answer == numbers[num]:
            correct += 1
        counter += 1
    
    print_results(done, correct, counter)


def extract_phone_numbers(n_repetitions, phone_min, phone_max):
    """
    Extract phone numbers from the list.
    """
    numbers_list = list()

    for i in range(n_repetitions):
        # Generate a random number between 0 and 100
        num = random.randint(0 if phone_min == 0 else 10**(phone_min-1), 10**phone_max-1)
        numbers_list.append(num)

    return numbers_list


def speak_phone_number(tts, number):
    from math import floor
    import os
    from voice import sd

    first_part_id = floor(len(number) * 0.4)
    parts = [number[id] for id in range(first_part_id)]

    second_part = number[first_part_id:]
    parts += [second_part[i:i+2] for i in range(0, len(second_part), 2)]

    logger.debug("Parts: %s", parts)

    os.makedirs("tmp", exist_ok=True)

    audios = list()
    sample_rates = list()

    for part in parts:
        audio, sample_rate = tts(str(part), immediately=False)
        audios.append(audio)
        sample_rates.append(sample_rate)

    for part, audio, sample_rate in zip(parts, audios, sample_rates):
        # Play the audio directly
        logger.debug("Playing audio for %s", part)
        sd.play(audio, samplerate=sample_rate)
        sd.wait()


def main_phone(n_repetitions, phone_min, phone_max, use_gpu):
    from voice import audio

    tests = extract_phone_numbers(n_repetitions, phone_min, phone_max)
    logger.debug("Generated phone numbers: %s", tests)

    counter = 0
    correct = 0

    done = list()

    tts = audio(model_type="tts_models/de/thorsten/tacotron2-DDC", use_gpu=use_gpu, verbose=logger.level == logging.DEBUG)  

    for i in range(n_repetitions):
        test = tests[i]

        logger.debug("Running example: %s", test)

        answer = "r"
        while answer == "r":
            speak_phone_number(tts, str(test))
            answer = input("Write the phone number in German ('r' to repeat, 'e' to exit): ")
            answer = answer.lower().strip()

        if answer == "e":
            break

        answer = str(int(answer))

        done.append((test, answer, str(test)))

        # Check if the answer is correct
        if answer == str(test):
            correct += 1
        counter += 1
    print_results(done, correct, counter)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Learn numbers in German.")
    parser.add_argument("-s", "--summary",      action="store_true", default=True, help="Show an initial summary of the numbers. Default is True.")
    parser.add_argument("-V", "--voice",        action="store_true", default=False, help="Use voice output for the numbers. Default is False.")
    parser.add_argument("-t", "--text",         action="store_true", default=False, help="Use text output for the numbers. Default is False.")
    parser.add_argument("-p", "--phone_min",    type=int, default=0, help="The minimum length of phone numbers. Default is 0.")
    parser.add_argument("-P", "--phone_max",    type=int, default=0, help="The maximum length of phone numbers. Default is 0.")
    parser.add_argument("-r", "--repetitions",  type=int, default=40, help="Number of repetitions for each number. Default is 40.")
    parser.add_argument("-G", "--gpu",          action="store_true", default=False, help="Use use_GPU for voice synthesis. Default is False.")
    parser.add_argument("-S", "--seed",         type=int, default=0, help="Set the random seed. Default is 0 and will use current time.")
    parser.add_argument("-l", "--log",          type=str, default="debug", choices=["debug", "info", "warning", "error", "disabled"], help="Set the log level. Default is debug.")
    args = parser.parse_args()

    # Set the log level
    if args.log == "debug":
        logger.setLevel(logging.DEBUG)
        logger.info("Arguments: %s", args)
        logger.debug("Summary: %s", args.summary)  
        logger.debug("Voice mode: %s", args.voice)
        logger.debug("Text mode: %s", args.text)
        logger.debug("Phone range: [%s %s]", args.phone_min, args.phone_max)
        logger.debug("Repetitions: %d", args.repetitions)
        logger.debug("GPU mode: %s", args.gpu)
        logger.debug("Seed: %d", args.seed)
        logger.debug("Log level: %s", args.log)
    elif args.log == "info":
        logger.setLevel(logging.INFO)
    elif args.log == "warning":
        logger.setLevel(logging.WARNING)
    elif args.log == "error":
        logger.setLevel(logging.ERROR)
    elif args.log == "disabled":
        logger.setLevel(logging.CRITICAL)

    if args.voice and args.text:
        raise RuntimeError("Please choose either voice or text output, not both.")
    if not (args.voice or args.text or (args.phone_min != 0 and args.phone_max != 0)):
        raise RuntimeError("Please choose either voice or text output.")
    
    if args.use_gpu and not args.voice:
        logger.debug("GPU option not considered, because voice is not selected.")

    if args.summary:
        help_message()

    # Set the random seed
    if args.seed == 0:
        import time
        args.seed = int(time.time())
    random.seed(args.seed)

    # Execute
    if args.phone_min != 0 and args.phone_max != 0:
        logger.debug("Running in phone mode.")
        main_phone(n_repetitions=args.repetitions, phone_min=args.phone_min, phone_max=args.phone_max, use_gpu=args.gpu)
    elif args.voice:
        logger.debug("Running in voice mode.")
        main_voice(n_repetitions=args.repetitions, use_gpu=args.gpu)
    elif args.text:
        logger.debug("Running in text mode.")
        main_text(n_repetitions=args.repetitions)
    else:
        raise RuntimeError("Please choose either voice, text or phone numbers.")
    
    print("Seed used: ", args.seed)


# ü
# ß


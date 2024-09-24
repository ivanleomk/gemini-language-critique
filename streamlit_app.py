import streamlit as st
from st_audiorec import st_audiorec
from jinja2 import Template
from model import PronounciationEvaluation
import google.generativeai as genai
import instructor
from pydub import AudioSegment

text = """
La vie en France est très différente de celle au Canada. Ici, il fait toujours chaud. Chaque dimanche, nous allons à la magnifique plage de Biarritz et nous achetons des glaces après avoir nagé dans la mer.

Les Français sont très sympathiques et accueillants. Nous parlons français lorsque nous sommes dehors, à l'école ou au marché. Cependant, nous continuons de parler anglais à la maison, car mes parents ne veulent pas que je perde ma langue natale.
"""

prompt = """
<rules>
    <rule>You're a world-class pronunciation teacher. Evaluate the pronunciation of the following text in the recording provided and provide a summary of the mistakes and how to correct them.</rule>
    <rule>Identify only the top 3 most important pronunciation mistakes in the text. For each mistake:</rule>
    <rule>
        <subrule>1. Provide the start timestamp (about 2 seconds before the word is mispronounced) in mm:ss format.</subrule>
        <subrule>2. Provide the end timestamp (about 2 seconds after the word is mispronounced) in mm:ss format.</subrule>
        <subrule>3. Include the entire sentence from the original text that contains the mispronounced word.</subrule>
        <subrule>4. Provide some tips to correct the mistake.</subrule>
    </rule>
    <rule>Once you've identified the top 3 most important pronunciation mistakes, provide a list of 4 potential words that have similar pronunciation that the speaker should practice to improve their pronunciation. These words should not be from the original text, but should be unrelated words that are likely to help the speaker improve their pronunciation.</rule>
</rules>

<emphasis>
    Important: When referencing a mispronounced word, always include the entire sentence from the original text in which it appears. Only select a single word as the mispronounced word within that sentence.
</emphasis>

<Original Text>
{{text}}
</Original Text>
"""

template = Template(prompt).render(text=text)

st.title("🎈 Pronunciation Evaluation")

st.title("Audio Recorder")

st.write(text)

wav_audio_data = st_audiorec()

if wav_audio_data is not None:
    st.audio(wav_audio_data, format="audio/wav")

st.session_state.audio_data = AudioSegment(wav_audio_data)
# To play audio in frontend:


# To save audio to a file, use pydub export method:


if "resp" not in st.session_state:
    st.session_state.resp = None

google_api_key = st.secrets["GOOGLE_API_KEY"]
genai.configure(api_key=google_api_key)
model = genai.GenerativeModel(model_name="models/gemini-1.5-pro-001")

client = instructor.from_gemini(
    client=model, mode=instructor.Mode.GEMINI_JSON, use_async=False
)


def analyze_text():
    # Read in the Google API key from Streamlit secrets

    st.session_state.resp = client.chat.completions.create(
        # model=model,
        response_model=PronounciationEvaluation,
        messages=[
            {
                "role": "user",
                "content": [
                    prompt.format(text=text),
                    {
                        "mime_type": "audio/mp3",
                        "data": st.session_state.audio_data.export().read(),
                    },
                ],
            },
        ],
        validation_context={
            "text": text,
        },
        max_retries=6,
    )


st.button("Analyze Text", on_click=analyze_text)

if st.session_state.resp:
    resp = st.session_state.resp
    # st.subheader("Pronunciation Mistakes")
    with open("mistakes.json", "w+") as f:
        f.write(resp.model_dump_json())

    for mistake in resp.mistakes:
        st.markdown(f"**Mispronounced word:** {mistake.mispronounced_word}")

        # Find the best match for the mispronounced word in the sentence
        # Find the best matching substring for the mispronounced word in the sentence

        st.markdown(f"**Sentence:** {mistake.highlighted_sentence}")

        def time_to_seconds(time_str):
            return sum(
                int(x) * 60**i for i, x in enumerate(reversed(time_str.split(":")))
            )

        start_time = max(
            0, time_to_seconds(mistake.start_ts)
        )  # Ensure start_time is not negative
        end_time = time_to_seconds(mistake.end_ts)

        # Ensure end_time doesn't exceed audio duration
        audio_duration = (
            len(st.session_state.audio_data) / 1000
        )  # Convert milliseconds to seconds
        end_time = min(end_time, audio_duration)

        # Extract the segment from start_time to end_time
        start_index = max(
            0, int(start_time * 1000) - 2000
        )  # Guard against negative index and add 2 seconds
        end_index = min(
            int(end_time * 1000) + 2000, len(st.session_state.audio_data)
        )  # Ensure end_index does not exceed audio length
        segment = st.session_state.audio_data[start_index:end_index]

        st.audio(segment.export().read())

        st.markdown(f"**Tips:** {mistake.tips}")
        st.markdown("---")

    st.subheader("Summary")
    st.write(resp.summary)

    st.subheader("Words to Practice")
    st.write(", ".join(resp.words_to_practice))

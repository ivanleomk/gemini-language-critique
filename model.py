from pydantic import BaseModel, Field, ValidationInfo, model_validator
from fuzzywuzzy import process
from typing_extensions import Self


class Mistake(BaseModel):
    start_ts: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    end_ts: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    mispronounced_word: str
    sentence: str
    tips: str

    @property
    def highlighted_sentence(self) -> str:
        sentence_parts = self.sentence.split(self.mispronounced_word)
        return f"{sentence_parts[0]}[{self.mispronounced_word}]{sentence_parts[1]}"

    @model_validator(mode="after")
    def validate_citations(self, info: ValidationInfo) -> Self:
        if info.context.get("text", "") is None:
            raise ValueError("No text provided to validate citations")

        sentences = [
            item.strip()
            for item in info.context.get("text", "").split(".")
            if item.strip()
        ]

        if self.sentence not in sentences:
            raise ValueError(
                f"Sentence '{self.sentence}' not found in the original text. Available sentences are: {sentences}. Make sure to cite the entire sentence from the original text."
            )

        if self.mispronounced_word not in self.sentence:
            raise ValueError(
                f"""Mispronounced word '{self.mispronounced_word}' not found in the original text of {self.sentence} and no close match found. 
                
                Make sure to cite the correct word and to use a word from the sentence itself.
                """
            )

        return self


class PronounciationEvaluation(BaseModel):
    mistakes: list[Mistake]
    summary: str
    words_to_practice: list[str]

import pypdf
from pathlib import Path
from config import RESUME_PATH

class ResumeParser:
    def __init__(self, file_path: Path = RESUME_PATH):
        self.file_path = file_path
        self._raw_text = None

    def get_text(self) -> str:
        if self._raw_text is not None:
            return self._raw_text

        if not self.file_path.exists():
            raise FileNotFoundError(f"Resume file not found at: {self.file_path}")

        reader = pypdf.PdfReader(str(self.file_path))
        extracted = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                extracted.append(text.strip())

        self._raw_text = "\n\n".join(extracted)
        return self._raw_text

    def get_summary(self, max_length: int = 3500) -> str:
        text = self.get_text()
        if len(text) <= max_length:
            return text
        return text[:max_length] + "\n...[truncated for length]..."

if __name__ == "__main__":
    parser = ResumeParser()
    resume_text = parser.get_text()
    print(f"Extracted {len(resume_text)} characters from resume.")

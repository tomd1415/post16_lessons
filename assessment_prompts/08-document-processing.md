# Document Processing

How to extract content from teacher-uploaded lesson materials.

## Overview

The system supports the NCCE (National Centre for Computing Education) Teach Computing curriculum format.

### Curriculum-Level Documents (in KS3 folder root)

| File | Contents |
|------|----------|
| `KS3 TCC Curriculum Map_v1.1.xlsx` | Full curriculum mapping: National Curriculum statements → Units → Lessons → Learning Objectives, Taxonomy strands |
| `NCCE - Teacher Guide KS3 - 1.1.pdf` | Pedagogy guidance, assessment approaches, progression, adaptation advice |

### Teach Computing Taxonomy (10 Strands)

The curriculum uses these taxonomy strands to categorise learning objectives:

| Code | Strand | Description |
|------|--------|-------------|
| NW | Networks | Understand how networks retrieve/share information and associated risks |
| CM | Creating Media | Select and create media including text, images, sounds, video |
| DI | Data and Information | Understand how data is stored, organised, and represents real-world scenarios |
| DD | Design and Development | Understand planning, creating, and evaluating computing artefacts |
| CS | Computing Systems | Understand what a computer is and how its parts function together |
| IT | Impact of Technology | Understand how individuals/society interact with computer systems |
| AL | Algorithms | Comprehend, design, create, and evaluate algorithms |
| PG | Programming | Create software to allow computers to solve problems |
| ET | Effective Use of Tools | Use software tools to support computing work |
| SS | Safety and Security | Understand risks when using technology and how to protect systems |

These strands help the AI categorise questions and ensure coverage across the curriculum.

### Assessment Approaches (from Teacher Guide)

The NCCE recommends two summative assessment types:
1. **Multiple Choice Quiz (MCQ)** - Quick knowledge checks
2. **Rubric-based assessment** - For project/practical work

The system should generate MCQ-style assessments aligned with this approach.

## Unit Structure

The system supports the NCCE Teach Computing curriculum format, which includes:

### Unit Structure (typical folder contents)
```
unit3/
├── Unit guide_3_Networks from semaphores to the Internet_Y7_v1.2.docx
├── Learning graph - Networks - Y7.pdf
├── Summative assessment – Networks – Y7.docx
├── Summative assessment answers – Networks – Y7.docx
├── L1 – Computer networks and protocols.zip
├── L2 – Networking hardware.zip
├── L3 – Wired and wireless networks.zip
├── L4 - The Internet.zip
├── L5 – Internet services.zip
└── L6 – The World Wide Web.zip
```

### Lesson Zip Contents
Each lesson .zip contains:
- **Lesson plan** (.docx) - Learning objectives, key vocabulary, activities
- **Slides** (.pptx) - Presentation slides for the lesson
- **Worksheets** (.docx) - Student activity sheets
- **Optional resources** - Images, additional materials

### Key Document Types

| Document | Contains | Use For Assessment |
|----------|----------|-------------------|
| Unit guide | Unit overview, lesson summaries, learning objectives, key vocabulary, misconceptions | Primary source for objectives and vocabulary |
| Lesson plans | Detailed LOs, vocabulary, activity descriptions | Detailed question context |
| Slides | Content, diagrams, examples | Visual content, examples |
| Summative assessment | Existing assessment questions | Reference/adaptation |
| Learning graph | Progression mapping | Understanding difficulty levels |

The system extracts text and structure to feed to the AI for question generation.

## Dependencies

```txt
# requirements.txt additions
python-docx>=1.1.0
python-pptx>=0.6.23
Pillow>=10.0.0  # For image handling
PyMuPDF>=1.23.0  # For PDF processing (learning graphs)
openpyxl>=3.1.0  # For Excel curriculum map processing
```

## Curriculum Map Processing (Optional)

The curriculum map Excel file can be parsed to:
- Get the full list of units and lessons for each year group
- Map learning objectives to taxonomy strands
- Ensure generated assessments align with national curriculum requirements

```python
# backend/app/services/curriculum_map.py

import openpyxl
from dataclasses import dataclass

@dataclass
class CurriculumObjective:
    year_group: int
    unit_name: str
    lesson_number: int
    learning_objective: str
    taxonomy_strands: list[str]  # e.g., ['NW', 'CS']
    nc_statement: str  # National Curriculum statement reference


class CurriculumMapParser:
    """Parse the NCCE curriculum map Excel file."""

    TAXONOMY_CODES = ['NW', 'CM', 'DI', 'DD', 'CS', 'IT', 'AL', 'PG', 'ET', 'SS']

    def parse(self, xlsx_path: str) -> list[CurriculumObjective]:
        """Extract curriculum objectives from the map."""
        workbook = openpyxl.load_workbook(xlsx_path, data_only=True)
        # Main data is typically on the second sheet
        sheet = workbook.worksheets[1] if len(workbook.worksheets) > 1 else workbook.active

        objectives = []
        for row in sheet.iter_rows(min_row=2, values_only=True):
            # Parse row based on column structure
            # Columns typically: Year, Order, Unit, Lesson, LO, Taxonomy tags, NC ref
            if row[0] and row[2]:  # Has year and unit
                objectives.append(CurriculumObjective(
                    year_group=int(row[0]) if isinstance(row[0], (int, float)) else 7,
                    unit_name=str(row[2]),
                    lesson_number=int(row[3]) if row[3] else 0,
                    learning_objective=str(row[4]) if row[4] else '',
                    taxonomy_strands=self._extract_strands(row),
                    nc_statement=str(row[-1]) if row[-1] else ''
                ))

        return objectives

    def _extract_strands(self, row) -> list[str]:
        """Extract taxonomy strand codes from row."""
        strands = []
        row_text = ' '.join(str(cell) for cell in row if cell)
        for code in self.TAXONOMY_CODES:
            if code in row_text:
                strands.append(code)
        return strands

    def get_objectives_for_unit(self, objectives: list, unit_name: str) -> list[CurriculumObjective]:
        """Filter objectives for a specific unit."""
        return [o for o in objectives if unit_name.lower() in o.unit_name.lower()]
```

## Unit Processing (Handling Zip Files)

```python
# backend/app/services/unit_processor.py

import zipfile
import tempfile
import os
from pathlib import Path
from dataclasses import dataclass

@dataclass
class NCCEUnit:
    """Parsed NCCE curriculum unit."""
    title: str
    year_group: int
    unit_number: int

    # From unit guide
    introduction: str
    lesson_summaries: list[dict]  # {lesson_num, title, overview, objectives}
    key_vocabulary: list[dict]    # {term, definition}
    misconceptions: list[dict]    # {misconception, guidance}
    curriculum_links: list[str]

    # From lesson materials
    lessons: list['ParsedLesson']

    # From summative assessment (if present)
    existing_questions: list[dict]


@dataclass
class ParsedLesson:
    """Content from a single lesson zip."""
    lesson_number: int
    title: str
    lesson_plan: 'ParsedDocument'
    slides: 'ParsedPresentation'
    worksheets: list['ParsedDocument']


class NCCEUnitProcessor:
    """Process NCCE Teach Computing curriculum units."""

    def __init__(self):
        self.docx_parser = DocxParser()
        self.pptx_parser = PptxParser()

    def process_unit_folder(self, folder_path: str) -> NCCEUnit:
        """Process all files in a unit folder."""
        folder = Path(folder_path)

        # Find and parse unit guide
        unit_guide = self._find_and_parse_unit_guide(folder)

        # Find and extract lesson zips
        lessons = []
        for zip_file in sorted(folder.glob("L*.zip")):
            lesson = self._process_lesson_zip(zip_file)
            if lesson:
                lessons.append(lesson)

        # Find and parse summative assessment
        existing_questions = self._parse_summative_assessment(folder)

        return NCCEUnit(
            title=unit_guide.get('title', ''),
            year_group=unit_guide.get('year_group', 7),
            unit_number=unit_guide.get('unit_number', 0),
            introduction=unit_guide.get('introduction', ''),
            lesson_summaries=unit_guide.get('lesson_summaries', []),
            key_vocabulary=unit_guide.get('vocabulary', []),
            misconceptions=unit_guide.get('misconceptions', []),
            curriculum_links=unit_guide.get('curriculum_links', []),
            lessons=lessons,
            existing_questions=existing_questions
        )

    def _process_lesson_zip(self, zip_path: Path) -> ParsedLesson:
        """Extract and parse contents of a lesson zip file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Extract zip
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(temp_dir)

            # Find the lesson folder (handles Mac __MACOSX folders)
            lesson_folder = None
            for item in Path(temp_dir).iterdir():
                if item.is_dir() and not item.name.startswith('__'):
                    lesson_folder = item
                    break

            if not lesson_folder:
                lesson_folder = Path(temp_dir)

            # Parse lesson plan
            lesson_plan = None
            for docx in lesson_folder.glob("*Lesson plan*.docx"):
                lesson_plan = self.docx_parser.parse(str(docx))
                break

            # Parse slides
            slides = None
            for pptx in lesson_folder.glob("*Slides*.pptx"):
                slides = self.pptx_parser.parse(str(pptx))
                break

            # Parse worksheets
            worksheets = []
            for docx in lesson_folder.glob("*.docx"):
                if "Lesson plan" not in docx.name and "Change log" not in docx.name:
                    worksheets.append(self.docx_parser.parse(str(docx)))

            # Extract lesson number from filename (e.g., "L1", "L2")
            lesson_num = 0
            import re
            match = re.search(r'L(\d+)', zip_path.name)
            if match:
                lesson_num = int(match.group(1))

            return ParsedLesson(
                lesson_number=lesson_num,
                title=lesson_plan.title if lesson_plan else '',
                lesson_plan=lesson_plan,
                slides=slides,
                worksheets=worksheets
            )

    def _find_and_parse_unit_guide(self, folder: Path) -> dict:
        """Parse the unit guide document."""
        for docx in folder.glob("Unit guide*.docx"):
            doc = self.docx_parser.parse(str(docx))
            return self._extract_unit_guide_structure(doc)
        return {}

    def _extract_unit_guide_structure(self, doc: 'ParsedDocument') -> dict:
        """Extract structured data from NCCE unit guide format."""
        result = {
            'title': doc.title,
            'introduction': '',
            'lesson_summaries': [],
            'vocabulary': doc.vocabulary,
            'misconceptions': [],
            'curriculum_links': []
        }

        # Unit guides have a specific table structure for lessons
        for table in doc.tables:
            if 'Lesson' in str(table.get('headers', [])):
                for row in table.get('rows', []):
                    if isinstance(row, dict):
                        result['lesson_summaries'].append({
                            'title': row.get('Lesson', ''),
                            'overview': row.get('Brief overview', ''),
                            'objectives': row.get('Learning objectives', '')
                        })

        # Extract misconceptions from dedicated section
        for section in doc.sections:
            heading = section.get('heading', '').lower()
            content = section.get('content', '')

            if 'introduction' in heading:
                result['introduction'] = content
            elif 'misconception' in heading:
                # Parse misconception table or list
                pass
            elif 'curriculum' in heading:
                result['curriculum_links'].append(content)

        return result

    def _parse_summative_assessment(self, folder: Path) -> list[dict]:
        """Parse existing summative assessment for reference."""
        questions = []

        for docx in folder.glob("Summative assessment*.docx"):
            if "answers" in docx.name.lower():
                continue  # Skip answers file, parse questions file

            doc = self.docx_parser.parse(str(docx))
            # Extract question structures from the assessment
            # NCCE assessments are typically multiple choice
            questions.extend(self._extract_existing_questions(doc))

        return questions

    def _extract_existing_questions(self, doc: 'ParsedDocument') -> list[dict]:
        """Extract question structures from existing assessment."""
        # Implementation depends on assessment format
        # NCCE typically uses numbered questions with options
        return []
```

## Word Document Processing (.docx)

```python
# backend/app/services/document_parser.py

from docx import Document
from docx.shared import Inches
import re
from typing import Optional
from dataclasses import dataclass

@dataclass
class ParsedDocument:
    """Structured content extracted from a document."""
    title: str
    raw_text: str
    sections: list[dict]
    learning_objectives: list[str]
    vocabulary: list[dict]
    activities: list[dict]
    tables: list[dict]
    images: list[bytes]


class DocxParser:
    """Parse Word documents to extract lesson content."""

    def __init__(self):
        self.lo_patterns = [
            r'learning\s*objectives?:?',
            r'pupils?\s*will\s*(?:be able to|learn)',
            r'by\s*the\s*end.*?students?\s*will',
            r'success\s*criteria:?',
            r'i\s*can\s*statements?:?'
        ]
        self.vocab_patterns = [
            r'key\s*(?:words?|vocabulary|terms?):?',
            r'glossary:?',
            r'definitions?:?'
        ]

    def parse(self, file_path: str) -> ParsedDocument:
        """Parse a .docx file and extract structured content."""
        doc = Document(file_path)

        # Extract raw text
        raw_text = self._extract_raw_text(doc)

        # Extract structured sections
        sections = self._extract_sections(doc)

        # Find learning objectives
        learning_objectives = self._extract_learning_objectives(doc, raw_text)

        # Find vocabulary
        vocabulary = self._extract_vocabulary(doc, raw_text)

        # Find activities/tasks
        activities = self._extract_activities(doc)

        # Extract tables (often contain key info)
        tables = self._extract_tables(doc)

        # Extract images (optional, for diagram questions)
        images = self._extract_images(doc)

        # Get title from first heading or filename
        title = self._extract_title(doc, file_path)

        return ParsedDocument(
            title=title,
            raw_text=raw_text,
            sections=sections,
            learning_objectives=learning_objectives,
            vocabulary=vocabulary,
            activities=activities,
            tables=tables,
            images=images
        )

    def _extract_raw_text(self, doc: Document) -> str:
        """Get all text from document."""
        paragraphs = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                paragraphs.append(text)
        return "\n\n".join(paragraphs)

    def _extract_sections(self, doc: Document) -> list[dict]:
        """Extract content organized by headings."""
        sections = []
        current_section = {"heading": "Introduction", "content": [], "level": 0}

        for para in doc.paragraphs:
            # Check if this is a heading
            if para.style.name.startswith('Heading'):
                # Save previous section
                if current_section["content"]:
                    current_section["content"] = "\n".join(current_section["content"])
                    sections.append(current_section)

                # Start new section
                level = int(para.style.name.replace('Heading ', '') or 1)
                current_section = {
                    "heading": para.text.strip(),
                    "content": [],
                    "level": level
                }
            else:
                text = para.text.strip()
                if text:
                    current_section["content"].append(text)

        # Don't forget last section
        if current_section["content"]:
            current_section["content"] = "\n".join(current_section["content"])
            sections.append(current_section)

        return sections

    def _extract_learning_objectives(self, doc: Document, raw_text: str) -> list[str]:
        """Find and extract learning objectives."""
        objectives = []

        # Look for LO section
        for pattern in self.lo_patterns:
            match = re.search(pattern, raw_text, re.IGNORECASE)
            if match:
                # Extract text after the match until next section
                start = match.end()
                # Find where LOs end (next heading or empty lines)
                end_patterns = [r'\n\s*\n\s*\n', r'\n[A-Z][a-z]+:']
                end = len(raw_text)
                for end_pattern in end_patterns:
                    end_match = re.search(end_pattern, raw_text[start:])
                    if end_match:
                        end = min(end, start + end_match.start())

                lo_text = raw_text[start:end]

                # Parse individual objectives (usually bulleted or numbered)
                lines = lo_text.split('\n')
                for line in lines:
                    line = line.strip()
                    # Remove bullet points, numbers, etc.
                    line = re.sub(r'^[\d\.\)\-\*\•]+\s*', '', line)
                    if line and len(line) > 10:  # Skip very short lines
                        objectives.append(line)
                break

        return objectives

    def _extract_vocabulary(self, doc: Document, raw_text: str) -> list[dict]:
        """Extract key vocabulary with definitions."""
        vocabulary = []

        for pattern in self.vocab_patterns:
            match = re.search(pattern, raw_text, re.IGNORECASE)
            if match:
                start = match.end()
                # Find end of vocabulary section
                end = min(start + 2000, len(raw_text))  # Limit search

                vocab_text = raw_text[start:end]

                # Look for "term - definition" or "term: definition" patterns
                term_patterns = [
                    r'([A-Za-z\s]+)\s*[-–:]\s*(.+?)(?=\n|$)',
                    r'\*\*([A-Za-z\s]+)\*\*\s*[-–:]?\s*(.+?)(?=\n|$)'
                ]

                for term_pattern in term_patterns:
                    matches = re.findall(term_pattern, vocab_text)
                    for term, definition in matches:
                        term = term.strip()
                        definition = definition.strip()
                        if term and definition and len(term) < 50:
                            vocabulary.append({
                                "term": term,
                                "definition": definition
                            })
                break

        return vocabulary

    def _extract_activities(self, doc: Document) -> list[dict]:
        """Extract described activities/tasks."""
        activities = []

        activity_keywords = ['activity', 'task', 'exercise', 'challenge', 'do now', 'starter']

        for i, para in enumerate(doc.paragraphs):
            text = para.text.lower()
            for keyword in activity_keywords:
                if keyword in text:
                    # Get this paragraph and following ones as activity description
                    activity_text = [doc.paragraphs[i].text]
                    # Get next few paragraphs that aren't headings
                    for j in range(i + 1, min(i + 5, len(doc.paragraphs))):
                        next_para = doc.paragraphs[j]
                        if not next_para.style.name.startswith('Heading'):
                            if next_para.text.strip():
                                activity_text.append(next_para.text)
                        else:
                            break

                    activities.append({
                        "title": doc.paragraphs[i].text.strip(),
                        "description": "\n".join(activity_text[1:]) if len(activity_text) > 1 else ""
                    })
                    break

        return activities

    def _extract_tables(self, doc: Document) -> list[dict]:
        """Extract table data."""
        tables = []

        for table in doc.tables:
            table_data = []
            headers = []

            for i, row in enumerate(table.rows):
                row_data = [cell.text.strip() for cell in row.cells]

                if i == 0:
                    headers = row_data
                else:
                    if headers:
                        table_data.append(dict(zip(headers, row_data)))
                    else:
                        table_data.append(row_data)

            if table_data:
                tables.append({
                    "headers": headers,
                    "rows": table_data
                })

        return tables

    def _extract_images(self, doc: Document) -> list[bytes]:
        """Extract embedded images."""
        images = []

        for rel in doc.part.rels.values():
            if "image" in rel.reltype:
                images.append(rel.target_part.blob)

        return images

    def _extract_title(self, doc: Document, file_path: str) -> str:
        """Get document title."""
        # Try to get from first heading
        for para in doc.paragraphs:
            if para.style.name.startswith('Heading 1') or para.style.name == 'Title':
                if para.text.strip():
                    return para.text.strip()

        # Fall back to filename
        import os
        return os.path.splitext(os.path.basename(file_path))[0]
```

## PowerPoint Processing (.pptx)

```python
# backend/app/services/document_parser.py (continued)

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.shapes import MSO_SHAPE_TYPE

@dataclass
class ParsedPresentation:
    """Structured content extracted from a presentation."""
    title: str
    slides: list[dict]
    all_text: str
    images: list[bytes]
    notes: list[str]


class PptxParser:
    """Parse PowerPoint presentations to extract lesson content."""

    def parse(self, file_path: str) -> ParsedPresentation:
        """Parse a .pptx file and extract content."""
        prs = Presentation(file_path)

        slides = []
        all_text_parts = []
        images = []
        notes = []

        for i, slide in enumerate(prs.slides):
            slide_data = self._parse_slide(slide, i + 1)
            slides.append(slide_data)
            all_text_parts.append(slide_data['text'])

            # Extract notes
            if slide.has_notes_slide:
                notes_text = slide.notes_slide.notes_text_frame.text
                if notes_text.strip():
                    notes.append(notes_text.strip())

            # Extract images
            for shape in slide.shapes:
                if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                    images.append(shape.image.blob)

        # Get title from first slide
        title = slides[0]['title'] if slides else "Untitled Presentation"

        return ParsedPresentation(
            title=title,
            slides=slides,
            all_text="\n\n".join(all_text_parts),
            images=images,
            notes=notes
        )

    def _parse_slide(self, slide, slide_number: int) -> dict:
        """Extract content from a single slide."""
        title = ""
        content = []
        bullet_points = []

        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue

            # Check if this is a title placeholder
            if shape.is_placeholder:
                if hasattr(shape, 'placeholder_format'):
                    ph_type = shape.placeholder_format.type
                    if ph_type in [1, 3]:  # TITLE or CENTER_TITLE
                        title = shape.text.strip()
                        continue

            # Extract text from shape
            for paragraph in shape.text_frame.paragraphs:
                text = paragraph.text.strip()
                if text:
                    # Check indentation level for bullets
                    level = paragraph.level
                    if level > 0:
                        bullet_points.append({
                            "text": text,
                            "level": level
                        })
                    else:
                        content.append(text)

        return {
            "number": slide_number,
            "title": title,
            "content": content,
            "bullets": bullet_points,
            "text": self._format_slide_text(title, content, bullet_points)
        }

    def _format_slide_text(self, title: str, content: list, bullets: list) -> str:
        """Format slide content as readable text."""
        parts = []

        if title:
            parts.append(f"## {title}")

        for text in content:
            parts.append(text)

        for bullet in bullets:
            indent = "  " * bullet['level']
            parts.append(f"{indent}- {bullet['text']}")

        return "\n".join(parts)
```

## Unified Parser

```python
# backend/app/services/document_parser.py (continued)

from pathlib import Path
from dataclasses import dataclass
from typing import Union

@dataclass
class LessonContent:
    """Combined content from all lesson documents."""
    unit_title: str
    lesson_plans: list[ParsedDocument]
    presentations: list[ParsedPresentation]

    # Aggregated content for AI
    learning_objectives: list[str]
    vocabulary: list[dict]
    all_content: str  # Combined text for AI prompt

    def to_ai_prompt_content(self) -> dict:
        """Format content for AI generation prompt."""
        return {
            "lesson_plan": self._combine_lesson_plans(),
            "slides": self._combine_slides(),
            "vocabulary": self._format_vocabulary(),
            "objectives": self.learning_objectives
        }

    def _combine_lesson_plans(self) -> str:
        parts = []
        for doc in self.lesson_plans:
            parts.append(f"### {doc.title}\n\n{doc.raw_text}")
        return "\n\n---\n\n".join(parts)

    def _combine_slides(self) -> str:
        parts = []
        for pres in self.presentations:
            parts.append(f"### {pres.title}\n\n{pres.all_text}")
        return "\n\n---\n\n".join(parts)

    def _format_vocabulary(self) -> str:
        lines = []
        for item in self.vocabulary:
            lines.append(f"- **{item['term']}**: {item['definition']}")
        return "\n".join(lines)


class DocumentProcessor:
    """Process multiple documents for a unit."""

    def __init__(self):
        self.docx_parser = DocxParser()
        self.pptx_parser = PptxParser()

    def process_unit_documents(
        self,
        file_paths: list[str],
        unit_title: str
    ) -> LessonContent:
        """Process all documents for a unit."""
        lesson_plans = []
        presentations = []
        all_objectives = []
        all_vocabulary = []

        for path in file_paths:
            ext = Path(path).suffix.lower()

            if ext == '.docx':
                parsed = self.docx_parser.parse(path)
                lesson_plans.append(parsed)
                all_objectives.extend(parsed.learning_objectives)
                all_vocabulary.extend(parsed.vocabulary)

            elif ext == '.pptx':
                parsed = self.pptx_parser.parse(path)
                presentations.append(parsed)

        # Deduplicate objectives and vocabulary
        unique_objectives = list(dict.fromkeys(all_objectives))
        unique_vocabulary = self._dedupe_vocabulary(all_vocabulary)

        # Combine all text
        all_text_parts = []
        for doc in lesson_plans:
            all_text_parts.append(doc.raw_text)
        for pres in presentations:
            all_text_parts.append(pres.all_text)

        return LessonContent(
            unit_title=unit_title,
            lesson_plans=lesson_plans,
            presentations=presentations,
            learning_objectives=unique_objectives,
            vocabulary=unique_vocabulary,
            all_content="\n\n".join(all_text_parts)
        )

    def _dedupe_vocabulary(self, vocabulary: list[dict]) -> list[dict]:
        """Remove duplicate vocabulary entries."""
        seen = set()
        unique = []
        for item in vocabulary:
            term_lower = item['term'].lower()
            if term_lower not in seen:
                seen.add(term_lower)
                unique.append(item)
        return unique
```

## Upload Endpoint

```python
# backend/app/routers/documents.py

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import List
import tempfile
import os

router = APIRouter(prefix="/api/documents", tags=["documents"])

ALLOWED_EXTENSIONS = {'.docx', '.pptx'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

@router.post("/upload")
async def upload_documents(
    files: List[UploadFile] = File(...),
    unit_id: str = None,
    current_teacher: Teacher = Depends(get_current_teacher)
):
    """Upload lesson documents for processing."""

    # Validate files
    for file in files:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type {ext} not allowed. Use .docx or .pptx"
            )

    # Save files temporarily and process
    processor = DocumentProcessor()
    temp_paths = []

    try:
        for file in files:
            # Save to temp file
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=os.path.splitext(file.filename)[1]
            ) as tmp:
                content = await file.read()
                if len(content) > MAX_FILE_SIZE:
                    raise HTTPException(status_code=400, detail="File too large")
                tmp.write(content)
                temp_paths.append(tmp.name)

        # Process all documents
        lesson_content = processor.process_unit_documents(
            file_paths=temp_paths,
            unit_title="Uploaded Unit"
        )

        # Save extracted content to database
        unit_docs = []
        for i, file in enumerate(files):
            doc_record = await save_unit_document(
                unit_id=unit_id,
                filename=file.filename,
                extracted_text=lesson_content.all_content,
                uploaded_by=current_teacher.id
            )
            unit_docs.append(doc_record)

        return {
            "message": f"Processed {len(files)} documents",
            "learning_objectives": lesson_content.learning_objectives,
            "vocabulary_count": len(lesson_content.vocabulary),
            "total_content_length": len(lesson_content.all_content),
            "document_ids": [str(d.id) for d in unit_docs]
        }

    finally:
        # Clean up temp files
        for path in temp_paths:
            try:
                os.unlink(path)
            except:
                pass


@router.get("/{document_id}/preview")
async def preview_document(
    document_id: str,
    current_teacher: Teacher = Depends(get_current_teacher)
):
    """Get preview of extracted content."""
    doc = await get_unit_document(document_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "filename": doc.filename,
        "extracted_text": doc.extracted_text[:5000],  # First 5000 chars
        "full_length": len(doc.extracted_text)
    }
```

## Content Cleaning

```python
# backend/app/services/document_parser.py (continued)

import re

class ContentCleaner:
    """Clean and normalize extracted content."""

    def clean(self, text: str) -> str:
        """Clean extracted text for AI processing."""
        # Remove excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)

        # Remove page numbers and headers/footers
        text = re.sub(r'Page \d+ of \d+', '', text)
        text = re.sub(r'\d+\s*$', '', text, flags=re.MULTILINE)

        # Remove common non-content elements
        text = re.sub(r'Click to edit.*', '', text)
        text = re.sub(r'Insert (image|picture|diagram).*', '', text, flags=re.IGNORECASE)

        # Normalize quotes and dashes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        text = text.replace('–', '-').replace('—', '-')

        return text.strip()

    def truncate_for_ai(self, text: str, max_chars: int = 15000) -> str:
        """Truncate text while preserving structure."""
        if len(text) <= max_chars:
            return text

        # Try to cut at a section break
        truncated = text[:max_chars]
        last_section = truncated.rfind('\n\n')

        if last_section > max_chars * 0.8:
            truncated = truncated[:last_section]

        return truncated + "\n\n[Content truncated...]"
```

## Testing Document Processing

```python
# tests/test_document_parser.py

import pytest
from app.services.document_parser import DocxParser, PptxParser, DocumentProcessor

@pytest.fixture
def sample_docx(tmp_path):
    """Create a sample Word document for testing."""
    from docx import Document

    doc = Document()
    doc.add_heading('Unit 1: Introduction to Binary', level=1)

    doc.add_heading('Learning Objectives', level=2)
    doc.add_paragraph('Pupils will be able to:')
    doc.add_paragraph('• Convert binary to decimal', style='List Bullet')
    doc.add_paragraph('• Convert decimal to binary', style='List Bullet')

    doc.add_heading('Key Vocabulary', level=2)
    doc.add_paragraph('Binary - A number system using only 0 and 1')
    doc.add_paragraph('Bit - A single binary digit')

    path = tmp_path / "test_lesson.docx"
    doc.save(path)
    return str(path)

def test_extracts_learning_objectives(sample_docx):
    parser = DocxParser()
    result = parser.parse(sample_docx)

    assert len(result.learning_objectives) >= 2
    assert any('binary' in lo.lower() for lo in result.learning_objectives)

def test_extracts_vocabulary(sample_docx):
    parser = DocxParser()
    result = parser.parse(sample_docx)

    assert len(result.vocabulary) >= 1
    terms = [v['term'].lower() for v in result.vocabulary]
    assert 'binary' in terms or 'bit' in terms
```

## Error Handling

```python
class DocumentParseError(Exception):
    """Error parsing a document."""
    pass

class DocumentProcessor:
    # ... existing methods ...

    def process_unit_documents(self, file_paths: list[str], unit_title: str) -> LessonContent:
        """Process with error handling."""
        errors = []

        for path in file_paths:
            try:
                # ... parsing logic ...
                pass
            except Exception as e:
                errors.append({
                    "file": Path(path).name,
                    "error": str(e)
                })

        if errors and not lesson_plans and not presentations:
            raise DocumentParseError(f"All documents failed to parse: {errors}")

        # Continue with partial results if some succeeded
        return LessonContent(...)
```

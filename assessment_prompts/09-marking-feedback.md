# Marking and Feedback

Auto-marking logic and feedback generation for all question types.

## Marking Principles

1. **Partial credit where appropriate**: Reward progress, not just perfection
2. **Clear scoring**: Pupils and teachers should understand how marks are awarded
3. **Consistent feedback**: Same quality feedback whether correct, partial, or incorrect
4. **Educational focus**: Feedback teaches, doesn't just evaluate

## Marking Service

```python
# backend/app/services/marker.py

from typing import Optional
from dataclasses import dataclass
from decimal import Decimal
import re

@dataclass
class MarkResult:
    """Result of marking a single answer."""
    score: Decimal
    max_score: int
    is_correct: bool
    is_partial: bool
    feedback: str
    details: Optional[dict] = None  # Type-specific details


class Marker:
    """Auto-mark answers for all question types."""

    def mark(self, question: dict, answer: dict) -> MarkResult:
        """Mark an answer against a question."""
        question_type = question['type']

        marker_method = getattr(self, f'_mark_{question_type}', None)
        if not marker_method:
            raise ValueError(f"Unknown question type: {question_type}")

        return marker_method(question, answer)

    def _mark_multiple_choice(self, question: dict, answer: dict) -> MarkResult:
        """Mark multiple choice (single correct answer)."""
        type_data = question['type_data']
        selected = answer.get('selected_option')

        correct_option = next(
            (opt['id'] for opt in type_data['options'] if opt.get('is_correct')),
            None
        )

        is_correct = selected == correct_option
        score = Decimal(question['points']) if is_correct else Decimal(0)

        # Get feedback
        if is_correct:
            feedback = question['feedback_correct']
        else:
            # Check for distractor-specific feedback
            selected_opt = next(
                (opt for opt in type_data['options'] if opt['id'] == selected),
                None
            )
            if selected_opt and selected_opt.get('distractor_feedback'):
                feedback = selected_opt['distractor_feedback']
            else:
                feedback = question['feedback_incorrect']

        return MarkResult(
            score=score,
            max_score=question['points'],
            is_correct=is_correct,
            is_partial=False,
            feedback=feedback,
            details={'selected': selected, 'correct': correct_option}
        )

    def _mark_multiple_select(self, question: dict, answer: dict) -> MarkResult:
        """Mark multiple select (multiple correct answers possible)."""
        type_data = question['type_data']
        selected = set(answer.get('selected_options', []))

        correct_options = {
            opt['id'] for opt in type_data['options'] if opt.get('is_correct')
        }

        # Calculate score: (correct selections - wrong selections) / total correct
        correct_selected = len(selected & correct_options)
        wrong_selected = len(selected - correct_options)

        # Score formula: max(0, correct - wrong) / total_correct * points
        raw_score = max(0, correct_selected - wrong_selected)
        proportion = Decimal(raw_score) / Decimal(len(correct_options))
        score = proportion * Decimal(question['points'])

        is_correct = selected == correct_options
        is_partial = not is_correct and score > 0

        # Generate feedback
        if is_correct:
            feedback = question['feedback_correct']
        elif is_partial:
            feedback = question.get('feedback_partial', question['feedback_incorrect'])
            feedback = feedback.replace('{correct}', str(correct_selected))
            feedback = feedback.replace('{total}', str(len(correct_options)))
        else:
            feedback = question['feedback_incorrect']

        return MarkResult(
            score=score.quantize(Decimal('0.01')),
            max_score=question['points'],
            is_correct=is_correct,
            is_partial=is_partial,
            feedback=feedback,
            details={
                'selected': list(selected),
                'correct': list(correct_options),
                'correct_count': correct_selected,
                'wrong_count': wrong_selected
            }
        )

    def _mark_text_input(self, question: dict, answer: dict) -> MarkResult:
        """Mark short text input with keyword matching."""
        type_data = question['type_data']
        submitted = answer.get('text', '').strip()

        # Normalize if not case sensitive
        if not type_data.get('case_sensitive', False):
            submitted = submitted.lower()

        # Check accepted answers (ordered by points, highest first)
        accepted = sorted(
            type_data.get('accepted_answers', []),
            key=lambda x: x.get('points', 1),
            reverse=True
        )

        best_match = None
        for accepted_answer in accepted:
            match_text = accepted_answer['text']
            if not type_data.get('case_sensitive', False):
                match_text = match_text.lower()

            if submitted == match_text:
                best_match = accepted_answer
                break

        if best_match:
            points_fraction = Decimal(str(best_match.get('points', 1)))
            score = points_fraction * Decimal(question['points'])
            is_correct = points_fraction >= Decimal('1')
            is_partial = not is_correct and score > 0

            if is_correct:
                feedback = question['feedback_correct']
            else:
                feedback = question.get('feedback_partial', question['feedback_incorrect'])
        else:
            score = Decimal(0)
            is_correct = False
            is_partial = False
            feedback = question['feedback_incorrect']

        return MarkResult(
            score=score.quantize(Decimal('0.01')),
            max_score=question['points'],
            is_correct=is_correct,
            is_partial=is_partial,
            feedback=feedback,
            details={'submitted': submitted}
        )

    def _mark_matching(self, question: dict, answer: dict) -> MarkResult:
        """Mark matching/pairing questions."""
        type_data = question['type_data']
        submitted_pairs = {(p['left'], p['right']) for p in answer.get('pairs', [])}

        correct_pairs = {
            (p['left'], p['right']) for p in type_data['correct_pairs']
        }

        correct_count = len(submitted_pairs & correct_pairs)
        total_pairs = len(correct_pairs)

        proportion = Decimal(correct_count) / Decimal(total_pairs)
        score = proportion * Decimal(question['points'])

        is_correct = correct_count == total_pairs
        is_partial = not is_correct and correct_count > 0

        if is_correct:
            feedback = question['feedback_correct']
        elif is_partial:
            feedback = question.get('feedback_partial', question['feedback_incorrect'])
            feedback = feedback.replace('{correct}', str(correct_count))
            feedback = feedback.replace('{total}', str(total_pairs))
        else:
            feedback = question['feedback_incorrect']

        return MarkResult(
            score=score.quantize(Decimal('0.01')),
            max_score=question['points'],
            is_correct=is_correct,
            is_partial=is_partial,
            feedback=feedback,
            details={
                'submitted': list(submitted_pairs),
                'correct_count': correct_count,
                'total': total_pairs
            }
        )

    def _mark_ordering(self, question: dict, answer: dict) -> MarkResult:
        """Mark ordering/sequencing questions."""
        type_data = question['type_data']
        submitted_order = answer.get('order', [])

        # Build correct order
        items = sorted(type_data['items'], key=lambda x: x['correct_position'])
        correct_order = [item['id'] for item in items]

        # Count items in correct position
        correct_positions = sum(
            1 for i, item_id in enumerate(submitted_order)
            if i < len(correct_order) and item_id == correct_order[i]
        )

        proportion = Decimal(correct_positions) / Decimal(len(correct_order))
        score = proportion * Decimal(question['points'])

        is_correct = submitted_order == correct_order
        is_partial = not is_correct and correct_positions > 0

        if is_correct:
            feedback = question['feedback_correct']
        elif is_partial:
            feedback = question.get('feedback_partial', question['feedback_incorrect'])
            feedback = feedback.replace('{correct}', str(correct_positions))
            feedback = feedback.replace('{total}', str(len(correct_order)))
        else:
            feedback = question['feedback_incorrect']

        return MarkResult(
            score=score.quantize(Decimal('0.01')),
            max_score=question['points'],
            is_correct=is_correct,
            is_partial=is_partial,
            feedback=feedback,
            details={
                'submitted': submitted_order,
                'correct': correct_order,
                'positions_correct': correct_positions
            }
        )

    def _mark_python_code(self, question: dict, answer: dict) -> MarkResult:
        """Mark Python coding questions by running test cases."""
        type_data = question['type_data']
        code = answer.get('code', '')
        test_results = answer.get('test_results', [])

        # If test results not provided, we need to run the code
        if not test_results:
            test_results = self._run_python_tests(code, type_data)

        # Count passed tests
        visible_tests = [t for t in type_data['test_cases'] if t.get('visible', True)]
        hidden_tests = [t for t in type_data['test_cases'] if not t.get('visible', True)]

        visible_passed = sum(1 for r in test_results[:len(visible_tests)] if r.get('passed'))
        hidden_passed = sum(1 for r in test_results[len(visible_tests):] if r.get('passed'))

        total_visible = len(visible_tests)
        total_hidden = len(hidden_tests)
        total_tests = total_visible + total_hidden

        # Calculate score with hidden test weighting
        hidden_weight = type_data.get('hidden_test_weight', 0.5)

        if total_hidden > 0:
            visible_portion = (1 - hidden_weight) * (visible_passed / total_visible) if total_visible > 0 else 0
            hidden_portion = hidden_weight * (hidden_passed / total_hidden)
            proportion = Decimal(str(visible_portion + hidden_portion))
        else:
            proportion = Decimal(visible_passed) / Decimal(total_visible) if total_visible > 0 else Decimal(0)

        score = proportion * Decimal(question['points'])

        all_passed = (visible_passed == total_visible and hidden_passed == total_hidden)
        is_correct = all_passed
        is_partial = not is_correct and score > 0

        if is_correct:
            feedback = question['feedback_correct']
        elif is_partial:
            feedback = question.get('feedback_partial', question['feedback_incorrect'])
            feedback = feedback.replace('{passed}', str(visible_passed + hidden_passed))
            feedback = feedback.replace('{total}', str(total_tests))
        else:
            feedback = question['feedback_incorrect']

        return MarkResult(
            score=score.quantize(Decimal('0.01')),
            max_score=question['points'],
            is_correct=is_correct,
            is_partial=is_partial,
            feedback=feedback,
            details={
                'test_results': test_results,
                'visible_passed': visible_passed,
                'hidden_passed': hidden_passed,
                'total_visible': total_visible,
                'total_hidden': total_hidden
            }
        )

    def _run_python_tests(self, code: str, type_data: dict) -> list[dict]:
        """Run Python code against test cases (calls Python runner service)."""
        # This would call the sandboxed Python runner
        # For now, return structure
        from ..services.python_runner import run_code_with_tests
        return run_code_with_tests(code, type_data['test_cases'])

    def _mark_parsons(self, question: dict, answer: dict) -> MarkResult:
        """Mark Parsons problem (code arrangement)."""
        type_data = question['type_data']
        submitted_blocks = answer.get('blocks', [])

        # Check against main solution
        solution = type_data['solution']
        matches_main = self._check_parsons_solution(submitted_blocks, solution)

        # Check alternative solutions
        matches_alt = False
        if not matches_main:
            for alt_solution in type_data.get('alternative_solutions', []):
                if self._check_parsons_solution(submitted_blocks, alt_solution):
                    matches_alt = True
                    break

        is_correct = matches_main or matches_alt

        if is_correct:
            score = Decimal(question['points'])
            feedback = question['feedback_correct']
        else:
            # Calculate partial credit
            correct_positions = self._count_correct_parsons_positions(submitted_blocks, solution)
            proportion = Decimal(correct_positions) / Decimal(len(solution))
            score = proportion * Decimal(question['points'])

            if score > 0:
                feedback = question.get('feedback_partial', question['feedback_incorrect'])
            else:
                feedback = question['feedback_incorrect']

        is_partial = not is_correct and score > 0

        return MarkResult(
            score=score.quantize(Decimal('0.01')),
            max_score=question['points'],
            is_correct=is_correct,
            is_partial=is_partial,
            feedback=feedback,
            details={'submitted': submitted_blocks, 'correct': solution}
        )

    def _check_parsons_solution(self, submitted: list, solution: list) -> bool:
        """Check if submitted matches solution exactly."""
        if len(submitted) != len(solution):
            return False

        for sub, sol in zip(submitted, solution):
            if sub.get('block_id') != sol.get('block_id'):
                return False
            if sub.get('indent', 0) != sol.get('indent', 0):
                return False

        return True

    def _count_correct_parsons_positions(self, submitted: list, solution: list) -> int:
        """Count how many blocks are in correct position with correct indent."""
        correct = 0
        for i, sol in enumerate(solution):
            if i < len(submitted):
                sub = submitted[i]
                if (sub.get('block_id') == sol.get('block_id') and
                    sub.get('indent', 0) == sol.get('indent', 0)):
                    correct += 1
        return correct

    def _mark_binary_convert(self, question: dict, answer: dict) -> MarkResult:
        """Mark binary/decimal/hex conversion."""
        type_data = question['type_data']
        submitted = answer.get('answer', '').strip().upper()  # Uppercase for hex
        correct = str(type_data['correct_answer']).upper()

        is_correct = submitted == correct
        score = Decimal(question['points']) if is_correct else Decimal(0)

        if is_correct:
            feedback = question['feedback_correct']
        else:
            feedback = question['feedback_incorrect']

        return MarkResult(
            score=score,
            max_score=question['points'],
            is_correct=is_correct,
            is_partial=False,
            feedback=feedback,
            details={
                'submitted': submitted,
                'correct': correct,
                'conversion_type': type_data.get('conversion_type')
            }
        )

    def _mark_trace_table(self, question: dict, answer: dict) -> MarkResult:
        """Mark trace table questions."""
        type_data = question['type_data']
        submitted_values = answer.get('values', {})  # {step_var: value}

        cells_to_fill = type_data['cells_to_fill']
        trace_rows = type_data['trace_rows']

        correct_count = 0
        total_cells = len(cells_to_fill)

        for cell in cells_to_fill:
            step = cell['step']
            variable = cell['variable']
            key = f"{step}_{variable}"

            # Find correct value
            row = next((r for r in trace_rows if r['step'] == step), None)
            if row:
                correct_value = str(row['values'].get(variable, ''))
                submitted_value = str(submitted_values.get(key, '')).strip()

                if submitted_value == correct_value:
                    correct_count += 1

        proportion = Decimal(correct_count) / Decimal(total_cells) if total_cells > 0 else Decimal(0)
        score = proportion * Decimal(question['points'])

        is_correct = correct_count == total_cells
        is_partial = not is_correct and correct_count > 0

        if is_correct:
            feedback = question['feedback_correct']
        elif is_partial:
            feedback = question.get('feedback_partial', question['feedback_incorrect'])
            feedback = feedback.replace('{correct}', str(correct_count))
            feedback = feedback.replace('{total}', str(total_cells))
        else:
            feedback = question['feedback_incorrect']

        return MarkResult(
            score=score.quantize(Decimal('0.01')),
            max_score=question['points'],
            is_correct=is_correct,
            is_partial=is_partial,
            feedback=feedback,
            details={
                'correct_count': correct_count,
                'total_cells': total_cells
            }
        )
```

## Feedback Personalization

```python
# backend/app/services/feedback.py

class FeedbackGenerator:
    """Generate personalized, encouraging feedback."""

    ENCOURAGEMENT_PHRASES = [
        "You're making good progress!",
        "Keep going - you're learning!",
        "Nice effort!",
        "You're getting closer!",
        "Good thinking!",
    ]

    CORRECT_CELEBRATIONS = [
        "Excellent!",
        "Well done!",
        "That's right!",
        "Perfect!",
        "Great work!",
    ]

    def generate_feedback(
        self,
        result: MarkResult,
        question: dict,
        attempt_number: int = 1,
        hint_used: bool = False
    ) -> str:
        """Generate appropriate feedback based on result."""

        base_feedback = result.feedback

        # Add encouragement for partial credit
        if result.is_partial:
            import random
            encouragement = random.choice(self.ENCOURAGEMENT_PHRASES)
            base_feedback = f"{encouragement} {base_feedback}"

        # Acknowledge hint usage without penalty
        if hint_used and result.is_correct:
            base_feedback = f"{base_feedback} Great job using the hint to help you!"

        return base_feedback

    def generate_summary_feedback(
        self,
        total_score: Decimal,
        max_score: int,
        questions_answered: int,
        total_questions: int
    ) -> str:
        """Generate end-of-assessment summary feedback."""
        percentage = (total_score / Decimal(max_score)) * 100 if max_score > 0 else 0

        if percentage >= 80:
            return "Fantastic work! You've shown excellent understanding of this topic."
        elif percentage >= 60:
            return "Well done! You've demonstrated good knowledge. Keep practising the areas you found tricky."
        elif percentage >= 40:
            return "Good effort! You've shown understanding of some key concepts. Review the feedback on each question to help you improve."
        else:
            return "Thank you for completing this assessment. Don't worry - everyone finds some topics challenging. Review the feedback and ask your teacher if you need extra help."
```

## Extended Text (AI-Assisted Marking)

```python
# backend/app/services/marker.py (continued)

class ExtendedTextMarker:
    """AI-assisted marking for extended text responses."""

    def __init__(self, openai_client):
        self.client = openai_client

    async def mark_extended_text(
        self,
        question: dict,
        answer: dict
    ) -> MarkResult:
        """Use AI to mark extended text response."""
        type_data = question['type_data']
        submitted_text = answer.get('text', '')

        if not type_data.get('ai_marking_enabled', False):
            # Queue for teacher marking
            return MarkResult(
                score=Decimal(0),
                max_score=question['points'],
                is_correct=False,
                is_partial=False,
                feedback="Your answer has been submitted for teacher marking.",
                details={'needs_teacher_marking': True}
            )

        # Use AI to mark
        marking_prompt = f"""
You are marking a student's extended text response. Be encouraging but accurate.

Question: {question['question_text']}

Mark Scheme (total {type_data['marking_guide']['points_available']} points):
{self._format_mark_scheme(type_data['marking_guide']['mark_scheme'])}

Student's Response:
{submitted_text}

Provide your assessment as JSON:
{{
    "points_awarded": <number>,
    "criteria_met": ["criterion1", "criterion2"],
    "criteria_not_met": ["criterion3"],
    "feedback": "<encouraging feedback explaining what was good and what could be improved>"
}}
"""

        response = await self.client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": marking_prompt}],
            response_format={"type": "json_object"},
            max_tokens=500
        )

        result = json.loads(response.choices[0].message.content)

        points = Decimal(str(result['points_awarded']))
        max_points = type_data['marking_guide']['points_available']

        return MarkResult(
            score=points,
            max_score=max_points,
            is_correct=points == max_points,
            is_partial=0 < points < max_points,
            feedback=result['feedback'],
            details={
                'criteria_met': result['criteria_met'],
                'criteria_not_met': result['criteria_not_met'],
                'ai_marked': True
            }
        )

    def _format_mark_scheme(self, mark_scheme: list) -> str:
        lines = []
        for criterion in mark_scheme:
            lines.append(f"- {criterion['criterion']} ({criterion['points']} point(s))")
        return "\n".join(lines)
```

## Python Code Runner

```python
# backend/app/services/python_runner.py

import subprocess
import tempfile
import os
from typing import list

def run_code_with_tests(code: str, test_cases: list[dict]) -> list[dict]:
    """
    Run Python code against test cases in a sandboxed environment.

    This should use Docker or a similar sandboxing mechanism in production.
    """
    results = []

    for test in test_cases:
        result = run_single_test(code, test['input'], test['expected'])
        result['visible'] = test.get('visible', True)
        results.append(result)

    return results


def run_single_test(code: str, test_input: str, expected: str) -> dict:
    """Run a single test case."""

    # Combine code with test execution
    full_code = f"""
{code}

# Test execution
result = {test_input}
print(repr(result))
"""

    try:
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            delete=False
        ) as f:
            f.write(full_code)
            temp_path = f.name

        # Run with timeout (this should be Docker in production)
        result = subprocess.run(
            ['python3', temp_path],
            capture_output=True,
            text=True,
            timeout=5
        )

        os.unlink(temp_path)

        if result.returncode != 0:
            return {
                'input': test_input,
                'expected': expected,
                'actual': f"Error: {result.stderr.strip()}",
                'passed': False,
                'error': True
            }

        actual = result.stdout.strip()

        # Compare (handle repr formatting)
        actual_clean = actual.strip("'\"")
        expected_clean = expected.strip("'\"")

        passed = actual_clean == expected_clean

        return {
            'input': test_input,
            'expected': expected,
            'actual': actual_clean,
            'passed': passed,
            'error': False
        }

    except subprocess.TimeoutExpired:
        return {
            'input': test_input,
            'expected': expected,
            'actual': "Error: Code took too long to run",
            'passed': False,
            'error': True,
            'timeout': True
        }
    except Exception as e:
        return {
            'input': test_input,
            'expected': expected,
            'actual': f"Error: {str(e)}",
            'passed': False,
            'error': True
        }
```

## Statistics Aggregation

```python
# backend/app/services/analytics_service.py

async def update_question_statistics(question_id: UUID, answer: Answer):
    """Update aggregated statistics for a question after each answer."""
    stats = await get_or_create_question_stats(question_id)

    stats.attempts_count += 1

    if answer.is_correct:
        stats.correct_count += 1
    elif answer.score > 0:
        stats.partial_count += 1
    else:
        stats.incorrect_count += 1

    if answer.hint_used:
        stats.hint_usage_count += 1

    if answer.scaffold_used:
        stats.scaffold_usage_count += 1

    # Update average time
    if answer.time_taken_seconds:
        current_total = (stats.average_time_seconds or 0) * (stats.attempts_count - 1)
        stats.average_time_seconds = (current_total + answer.time_taken_seconds) // stats.attempts_count

    # For multiple choice, track option distribution
    if answer.answer_data.get('selected_option'):
        dist = stats.option_distribution or {}
        selected = answer.answer_data['selected_option']
        dist[selected] = dist.get(selected, 0) + 1
        stats.option_distribution = dist

    stats.updated_at = datetime.utcnow()
    await save_question_stats(stats)
```

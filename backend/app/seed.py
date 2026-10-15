"""
Idempotent database seed script for LearnWhy AI (PSM147 / QE4).
All demo users and sample records are explicitly labeled as seed/demo data.
"""
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, engine, Base
from app.core.security import hash_password
from app.models.entities import (
    Achievement,
    Activity,
    AnswerOption,
    Attempt,
    Concept,
    ConceptPrerequisite,
    Course,
    Diagnosis,
    InterventionOutcome,
    LearnerPreference,
    MasteryState,
    Misconception,
    Question,
    Recommendation,
    User,
    UserAchievement,
)
from app.services.audit import log_audit_event
from app.services.diagnosis import diagnose_attempt
from app.services.mastery import get_or_create_mastery_state, update_concept_mastery
from app.services.recommendation import generate_recommendations_for_user


FLOWCHART_SVG_RANGE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 520 150" role="img" aria-label="Flowchart of Python range(1, 4) loop execution">
  <rect x="10" y="35" width="110" height="60" rx="8" fill="#eff6ff" stroke="#1d4ed8" stroke-width="2"/>
  <text x="65" y="62" text-anchor="middle" font-family="monospace" font-size="12" fill="#1e3a8a">Start i = 1</text>
  <text x="65" y="80" text-anchor="middle" font-family="sans-serif" font-size="11" fill="#1e40af">(inclusive)</text>
  <line x1="120" y1="65" x2="165" y2="65" stroke="#475569" stroke-width="2"/>
  <rect x="165" y="35" width="150" height="60" rx="8" fill="#fef3c7" stroke="#b45309" stroke-width="2"/>
  <text x="240" y="60" text-anchor="middle" font-family="monospace" font-size="12" fill="#78350f">Check: i &lt; 4 ?</text>
  <text x="240" y="80" text-anchor="middle" font-family="sans-serif" font-size="11" fill="#92400e">Visits i = 1, 2, 3</text>
  <line x1="315" y1="65" x2="360" y2="65" stroke="#475569" stroke-width="2"/>
  <rect x="360" y="35" width="145" height="60" rx="8" fill="#dcfce7" stroke="#15803d" stroke-width="2"/>
  <text x="432" y="60" text-anchor="middle" font-family="monospace" font-size="12" fill="#14532d">Stop at i == 4</text>
  <text x="432" y="80" text-anchor="middle" font-family="sans-serif" font-size="11" fill="#166534">4 is excluded</text>
</svg>"""

FLOWCHART_SVG_IF_ELIF = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 520 150" role="img" aria-label="Comparison between if-elif chain and separate if statements">
  <rect x="12" y="25" width="230" height="95" rx="8" fill="#eff6ff" stroke="#1d4ed8" stroke-width="2"/>
  <text x="127" y="48" text-anchor="middle" font-family="sans-serif" font-weight="bold" font-size="12" fill="#1e3a8a">if / elif Chain (Mutually Exclusive)</text>
  <text x="127" y="70" text-anchor="middle" font-family="monospace" font-size="11" fill="#1e40af">First True branch runs;</text>
  <text x="127" y="90" text-anchor="middle" font-family="monospace" font-size="11" fill="#1e40af">remaining elif/else skipped.</text>
  <rect x="272" y="25" width="235" height="95" rx="8" fill="#fef2f2" stroke="#b91c1c" stroke-width="2"/>
  <text x="390" y="48" text-anchor="middle" font-family="sans-serif" font-weight="bold" font-size="12" fill="#7f1d1d">Separate if Blocks (Independent)</text>
  <text x="390" y="70" text-anchor="middle" font-family="monospace" font-size="11" fill="#991b1b">Every if condition is tested</text>
  <text x="390" y="90" text-anchor="middle" font-family="monospace" font-size="11" fill="#991b1b">even if an earlier if was True.</text>
</svg>"""

FLOWCHART_SVG_FUNC_RETURN = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 520 150" role="img" aria-label="Diagram contrasting print output with return value">
  <rect x="15" y="25" width="225" height="95" rx="8" fill="#fff7ed" stroke="#c2410c" stroke-width="2"/>
  <text x="127" y="50" text-anchor="middle" font-family="monospace" font-weight="bold" font-size="12" fill="#7c2d12">print(x) -&gt; Console Screen</text>
  <text x="127" y="74" text-anchor="middle" font-family="sans-serif" font-size="11" fill="#9a3412">Shows text to human reader.</text>
  <text x="127" y="94" text-anchor="middle" font-family="monospace" font-size="11" fill="#9a3412">Caller receives: None</text>
  <rect x="275" y="25" width="230" height="95" rx="8" fill="#ecfdf5" stroke="#047857" stroke-width="2"/>
  <text x="390" y="50" text-anchor="middle" font-family="monospace" font-weight="bold" font-size="12" fill="#064e3b">return x -&gt; Caller Variable</text>
  <text x="390" y="74" text-anchor="middle" font-family="sans-serif" font-size="11" fill="#065f46">Hands data back to expression.</text>
  <text x="390" y="94" text-anchor="middle" font-family="monospace" font-size="11" fill="#065f46">Caller receives: value of x</text>
</svg>"""


def seed_database(db: Session) -> None:
    # Check if already seeded
    existing_course = (
        db.query(Course)
        .filter(Course.slug == "python-foundations-101")
        .first()
    )
    if existing_course:
        return

    # 1. Create Python Course
    course = Course(
        slug="python-foundations-101",
        title="Python Programming Foundations (PSM147 Curated Curriculum)",
        description=(
            "A concept-mapped introductory Python curriculum covering variables, conditional logic, "
            "loops, functions, lists, and list iteration with misconception-aware diagnostics and "
            "multimodal remediation."
        ),
        status="published",
        version="1.0.0",
    )
    db.add(course)
    db.flush()

    # 2. Create 6 Core Python Concepts
    concepts_spec = [
        (
            "variables-expressions",
            "Variables & Expressions",
            "Sequential variable assignment, value binding, and data type operations in Python.",
            "Trace variable reassignments and distinguish string vs. numeric expressions.",
            1,
            0.45,
        ),
        (
            "conditions",
            "Conditions & Branching",
            "Boolean expressions, comparison operators, and mutually exclusive if/elif/else chains.",
            "Predict branch execution accurately across chained and compound conditions.",
            2,
            0.40,
        ),
        (
            "loops",
            "Loops & Stopping Conditions",
            "Definite and indefinite iteration using for/range() and while loops with accumulators.",
            "Determine loop bounds, iteration counts, and accumulator updates accurately.",
            3,
            0.35,
        ),
        (
            "functions",
            "Functions, Parameters & Return",
            "Defining reusable functions, passing arguments, local scope, and returning values.",
            "Distinguish return values from console print side-effects and trace parameter scope.",
            4,
            0.35,
        ),
        (
            "lists",
            "Lists, Indexing & Mutability",
            "Zero-based indexing, slicing, in-place list methods, and aliasing.",
            "Access list elements by zero-based index and distinguish in-place mutation from new lists.",
            5,
            0.40,
        ),
        (
            "list-iteration",
            "List Iteration & Filtering",
            "Traversing lists by element or index, accumulating results, and safe filtering patterns.",
            "Write and trace loops that process or filter list elements without index/value confusion.",
            6,
            0.30,
        ),
    ]

    concept_objs: dict[str, Concept] = {}
    for slug, name, desc, obj, order_idx, prior in concepts_spec:
        c = Concept(
            course_id=course.id,
            slug=slug,
            name=name,
            description=desc,
            learning_objective=obj,
            order_index=order_idx,
            prior_mastery=prior,
            status="published",
        )
        db.add(c)
        db.flush()
        concept_objs[slug] = c

    # 3. Prerequisite directed edges
    # variables-expressions -> conditions -> loops -> functions
    # variables-expressions -> lists
    # loops + lists -> list-iteration
    edges_spec = [
        ("conditions", "variables-expressions"),
        ("loops", "conditions"),
        ("functions", "loops"),
        ("lists", "variables-expressions"),
        ("list-iteration", "loops"),
        ("list-iteration", "lists"),
    ]
    for target_slug, prereq_slug in edges_spec:
        db.add(
            ConceptPrerequisite(
                concept_id=concept_objs[target_slug].id,
                prerequisite_id=concept_objs[prereq_slug].id,
            )
        )
    db.flush()

    # 4. Curated Misconceptions (transparent, versioned rules)
    misconceptions_spec = [
        (
            "MISC-VAR-REASSIGN",
            "variables-expressions",
            "Treating assignment as a live spreadsheet formula",
            "Believing that changing a variable later automatically updates other variables previously computed from it.",
            "Option assumes y = x + 2 automatically recomputes when x is reassigned on a later line.",
            "Python executes top-to-bottom: assignment binds the current value at that moment, not a permanent formula.",
        ),
        (
            "MISC-VAR-STR-INT",
            "variables-expressions",
            "Confusing string concatenation with numeric addition",
            "Expecting '4' + '2' to evaluate to integer 6 instead of string '42'.",
            "Option treats quoted numeric strings as integers during + operator evaluation.",
            "The + operator concatenates strings ('4' + '2' -> '42') and adds numbers (4 + 2 -> 6).",
        ),
        (
            "MISC-COND-ELIF-CHAIN",
            "conditions",
            "Treating separate 'if' statements as an 'if/elif' chain",
            "Assuming that when one 'if' block runs, a subsequent independent 'if' statement is skipped.",
            "Option overlooks that a second independent 'if' statement also evaluates to True and overwrites or appends output.",
            "Use 'elif' when branches must be mutually exclusive; separate 'if' statements are evaluated independently.",
        ),
        (
            "MISC-COND-TRUTHY-OR",
            "conditions",
            "Writing 'x == a or b' instead of 'x == a or x == b'",
            "Assuming Python's 'or' distributes across '==' like English phrasing.",
            "Option evaluates `status == 'admin' or 'editor'` as False when status is 'guest', forgetting `'editor'` is truthy.",
            "In Python, `'editor'` is a non-empty truthy string, so `x == 'a' or 'b'` is always truthy. Write `x in ('a', 'b')`.",
        ),
        (
            "MISC-LOOP-RANGE-STOP",
            "loops",
            "Off-by-one error: assuming range(start, stop) includes stop",
            "Expecting range(1, 4) to produce 1, 2, 3, 4 instead of stopping before 4.",
            "Selected distractor includes the upper stop bound of range(start, stop) in the loop iterations.",
            "Python's range(start, stop) is half-open [start, stop): it starts at `start` and stops strictly before `stop`.",
        ),
        (
            "MISC-LOOP-ACCUM-RESET",
            "loops",
            "Resetting the accumulator variable inside the loop body",
            "Placing `total = 0` inside the `for` loop so only the final iteration's value is retained.",
            "Selected distractor reflects accumulator reset inside loop or confusion with loop bound.",
            "Initialize accumulators (`total = 0`) once BEFORE the loop begins, and update (`total += x`) inside the loop.",
        ),
        (
            "MISC-FUNC-PRINT-RETURN",
            "functions",
            "Confusing print() console output with function return value",
            "Assuming a function that calls print(result) without a return statement hands that value back to the caller.",
            "Selected distractor treats printed text as the return value rather than None.",
            "`print()` displays text on the screen; `return` sends a value back to the caller. A function with no `return` returns `None`.",
        ),
        (
            "MISC-FUNC-LOCAL-SCOPE",
            "functions",
            "Assuming parameter reassignment mutates outer caller variables",
            "Believing that reassigning a parameter `x = x + 10` inside a function modifies the integer variable passed in.",
            "Selected distractor assumes local parameter rebinding mutates an immutable outer variable.",
            "Parameters are local names inside the function; reassigning an integer parameter does not change the caller's variable unless returned and reassigned.",
        ),
        (
            "MISC-LIST-ZERO-INDEX",
            "lists",
            "One-based indexing error (off-by-one list index)",
            "Treating `items[1]` as the first element of a list instead of `items[0]`.",
            "Selected distractor uses 1-based indexing instead of Python's 0-based indexing.",
            "Python lists are 0-indexed: index 0 is the first item, index 1 is the second item, and index -1 is the last item.",
        ),
        (
            "MISC-LIST-SORT-RETURN",
            "lists",
            "Assigning the result of list.sort() expecting a new list",
            "Writing `data = data.sort()` and expecting `data` to hold the sorted list instead of `None`.",
            "Selected distractor assumes in-place `.sort()` returns the sorted list object.",
            "`list.sort()` sorts the list in-place and returns `None`. Use `sorted(data)` if you need a new returned list.",
        ),
        (
            "MISC-ITER-INDEX-VALUE",
            "list-iteration",
            "Confusing loop variable element value with list index",
            "Writing `nums[x]` inside `for x in nums:` as if `x` were an index rather than the element itself.",
            "Selected distractor confuses direct element iteration (`for item in list`) with index iteration (`for i in range(len(list))`).",
            "In `for item in items:`, `item` is already the element value. Use `enumerate(items)` if you need both index and value.",
        ),
        (
            "MISC-ITER-FILTER-INDENT",
            "list-iteration",
            "Unconditional append or premature return inside a filtering loop",
            "Returning on the very first loop iteration instead of collecting all matching items first.",
            "Selected distractor overlooks that `return` inside a loop exits the function immediately on iteration 1.",
            "When filtering a list in a function, append matches inside the loop and place `return result` AFTER the loop finishes.",
        ),
    ]

    misc_objs: dict[str, Misconception] = {}
    for code, c_slug, label, desc, rule, focus in misconceptions_spec:
        m = Misconception(
            code=code,
            concept_id=concept_objs[c_slug].id,
            label=label,
            description=desc,
            diagnostic_rule=rule,
            remediation_focus=focus,
            rule_version="v1.0.0-rules",
            status="active",
        )
        db.add(m)
        db.flush()
        misc_objs[code] = m

    # 5. Curated Question Bank (Practice, Ambiguous + Diagnostic Follow-ups, and Fresh Verification items)
    questions_data = [
        # --- CONCEPT 1: VARIABLES & EXPRESSIONS ---
        {
            "stable_id": "PY-VAR-01",
            "concept_slug": "variables-expressions",
            "difficulty": 1,
            "is_verification_only": False,
            "is_diagnostic_followup": False,
            "content": "What does the following Python code print after all three lines run?",
            "code_snippet": "price = 10\ntotal = price + 5\nprice = 20\nprint(total)",
            "answer_key": "B",
            "explanation": "On line 2, `total` is assigned `10 + 5 = 15`. Reassigning `price = 20` on line 3 does not retroactively update `total` because Python variables store values, not live spreadsheet formulas.",
            "plain_language_explanation": "Line 2 saves the number 15 inside `total`. Changing `price` later on line 3 does not change `total` (सरल शब्दों में: Python लाइन-दर-लाइन चलता है, इसलिए `total` का मान 15 ही रहता है).",
            "worked_example": "x = 3\ny = x * 2  # y is now 6\nx = 100    # x changes to 100, but y is still 6",
            "hint_ladder": [
                "Trace the code one line at a time from top to bottom.",
                "What value does `price` have at the exact moment line 2 (`total = price + 5`) executes?",
                "Does line 3 ever assign a new value to `total`, or only to `price`?",
            ],
            "audio_transcript": "Audio transcript: Price starts at 10. Total is set to price plus 5, which is 15. Next, price is changed to 20, but total is not recalculated. Printing total outputs 15.",
            "options": [
                ("A", "25", "MISC-VAR-REASSIGN", None, 0.85, None, False),
                ("B", "15", None, None, 1.0, None, True),
                ("C", "20", None, None, 0.40, None, False),
                ("D", "10", None, None, 0.40, None, False),
            ],
        },
        {
            "stable_id": "PY-VAR-02",
            "concept_slug": "variables-expressions",
            "difficulty": 2,
            "is_verification_only": False,
            "is_diagnostic_followup": False,
            "content": "What is the output of this expression when executed in Python?",
            "code_snippet": "a = '4'\nb = '2'\nprint(a + b)",
            "answer_key": "C",
            "explanation": "Because `'4'` and `'2'` are enclosed in quotes, they are strings (`str`). The `+` operator between two strings performs string concatenation, producing `'42'`.",
            "plain_language_explanation": "Quotes make `'4'` and `'2'` text strings. Putting `+` between two text strings joins them side-by-side into `'42'` instead of adding them as numbers.",
            "worked_example": "'hello' + '!' -> 'hello!'\n'10' + '5' -> '105'\nint('10') + int('5') -> 15",
            "hint_ladder": [
                "Look closely at the quotation marks around `'4'` and `'2'`.",
                "What data type is `'4'` in Python: an integer (`int`) or a string (`str`)?",
                "How does the `+` operator behave when both operands are strings?",
            ],
            "audio_transcript": "Audio transcript: Variable a is the string '4' and variable b is the string '2'. Combining two strings with plus concatenates them into '42'.",
            "options": [
                ("A", "6", "MISC-VAR-STR-INT", None, 0.86, None, False),
                ("B", "8", None, None, 0.35, None, False),
                ("C", "42", None, None, 1.0, None, True),
                ("D", "TypeError", None, None, 0.35, None, False),
            ],
        },
        {
            "stable_id": "PY-VAR-VERIF-01",
            "concept_slug": "variables-expressions",
            "difficulty": 1,
            "is_verification_only": True,
            "is_diagnostic_followup": False,
            "content": "[Fresh Verification] After running the code below, what value is printed for `score_backup`?",
            "code_snippet": "score = 50\nscore_backup = score\nscore = score + 30\nprint(score_backup)",
            "answer_key": "A",
            "explanation": "`score_backup` bound the value `50` on line 2. Rebinding `score` to `80` on line 3 leaves `score_backup` pointing to `50`.",
            "plain_language_explanation": "`score_backup` saved 50 before `score` was increased. So `score_backup` stays 50.",
            "worked_example": "a = 7\nb = a\na = 99\nprint(b)  # prints 7",
            "hint_ladder": [
                "Check what value `score` holds when line 2 runs.",
                "Does line 3 modify `score_backup`?",
            ],
            "audio_transcript": "Verification question: score starts at 50, score_backup is set to score, and then score is increased by 30. What is printed for score_backup?",
            "options": [
                ("A", "50", None, None, 1.0, None, True),
                ("B", "80", "MISC-VAR-REASSIGN", None, 0.85, None, False),
                ("C", "30", None, None, 0.40, None, False),
                ("D", "0", None, None, 0.40, None, False),
            ],
        },

        # --- CONCEPT 2: CONDITIONS & BRANCHING ---
        {
            "stable_id": "PY-COND-01",
            "concept_slug": "conditions",
            "difficulty": 1,
            "is_verification_only": False,
            "is_diagnostic_followup": False,
            "content": "What value is stored in `label` after this code runs?",
            "code_snippet": "temp = 35\nlabel = 'normal'\nif temp > 30:\n    label = 'warm'\nif temp > 20:\n    label = 'mild'\nprint(label)",
            "answer_key": "C",
            "explanation": "Notice there are two separate `if` statements (not `if` / `elif`). When `temp = 35`, `temp > 30` is True (`label` becomes `'warm'`), and then the second independent `if temp > 20:` ALSO runs (`label` is overwritten with `'mild'`).",
            "plain_language_explanation": "Because the second check uses `if` instead of `elif`, Python checks both conditions. First `label` becomes `'warm'`, and then the second `if` changes it to `'mild'`.",
            "worked_example": "# Using elif keeps branches mutually exclusive:\nif temp > 30:\n    label = 'warm'\nelif temp > 20:\n    label = 'mild'",
            "diagram_svg": FLOWCHART_SVG_IF_ELIF,
            "hint_ladder": [
                "Look at line 5: does it say `elif temp > 20:` or `if temp > 20:`?",
                "When Python finishes the first `if` block, does it skip a separate `if` statement?",
                "Trace `label` after line 4, and then trace what happens on lines 5–6.",
            ],
            "audio_transcript": "Audio transcript: Temp is 35. The first if checks temp > 30 and sets label to warm. The second statement is a separate if temp > 20, which also evaluates to True and overwrites label with mild.",
            "options": [
                ("A", "warm", "MISC-COND-ELIF-CHAIN", None, 0.86, None, False),
                ("B", "normal", None, None, 0.40, None, False),
                ("C", "mild", None, None, 1.0, None, True),
                ("D", "warmmild", None, None, 0.40, None, False),
            ],
        },
        {
            "stable_id": "PY-COND-02",
            "concept_slug": "conditions",
            "difficulty": 2,
            "is_verification_only": False,
            "is_diagnostic_followup": False,
            "content": "What does the following conditional block print when `role = 'guest'`?",
            "code_snippet": "role = 'guest'\nif role == 'admin' or 'moderator':\n    print('Access granted')\nelse:\n    print('Access denied')",
            "answer_key": "A",
            "explanation": "Python parses `role == 'admin' or 'moderator'` as `(role == 'admin') or ('moderator')`. Since `'moderator'` is a non-empty string, it is always truthy in Python, so the `if` condition is always True!",
            "plain_language_explanation": "In Python, `'moderator'` by itself after `or` is treated as True because it is non-empty text. You must write `if role == 'admin' or role == 'moderator':`.",
            "worked_example": "# Correct way:\nif role == 'admin' or role == 'moderator':\n    ...\n# Or even cleaner:\nif role in ('admin', 'moderator'):\n    ...",
            "hint_ladder": [
                "How does Python group the operators in `role == 'admin' or 'moderator'`?",
                "What is the boolean truth value of a non-empty string like `bool('moderator')` in Python?",
                "If the left side of `or` is `False` and the right side is `'moderator'`, is the whole condition truthy?",
            ],
            "options": [
                ("A", "Access granted", None, None, 1.0, None, True),
                ("B", "Access denied", "MISC-COND-TRUTHY-OR", None, 0.88, None, False),
                ("C", "SyntaxError", None, None, 0.35, None, False),
                ("D", "None", None, None, 0.35, None, False),
            ],
        },
        {
            "stable_id": "PY-COND-VERIF-01",
            "concept_slug": "conditions",
            "difficulty": 2,
            "is_verification_only": True,
            "is_diagnostic_followup": False,
            "content": "[Fresh Verification] What is printed by the following grading snippet when `marks = 85`?",
            "code_snippet": "marks = 85\ngrade = 'C'\nif marks >= 80:\n    grade = 'A'\nif marks >= 60:\n    grade = 'B'\nprint(grade)",
            "answer_key": "B",
            "explanation": "Because the second condition uses an independent `if marks >= 60:` rather than `elif marks >= 60:`, both conditions are True for `85`, so `grade` is set to `'A'` and then overwritten by `'B'`.",
            "plain_language_explanation": "Since `if` is used twice instead of `elif`, both checks run for 85 and the second check changes `grade` to `'B'`.",
            "worked_example": "if marks >= 80:\n    grade = 'A'\nelif marks >= 60:\n    grade = 'B'  # skipped when marks is 85",
            "hint_ladder": [
                "Check whether line 5 starts with `if` or `elif`.",
                "Is `85 >= 60` True?",
            ],
            "options": [
                ("A", "A", "MISC-COND-ELIF-CHAIN", None, 0.86, None, False),
                ("B", "B", None, None, 1.0, None, True),
                ("C", "C", None, None, 0.35, None, False),
                ("D", "AB", None, None, 0.35, None, False),
            ],
        },

        # --- CONCEPT 3: LOOPS & STOPPING CONDITIONS (Includes Ambiguous Distractor + Follow-up!) ---
        {
            "stable_id": "PY-LOOP-01",
            "concept_slug": "loops",
            "difficulty": 1,
            "is_verification_only": False,
            "is_diagnostic_followup": False,
            "content": "What value is printed after this `for` loop finishes executing?",
            "code_snippet": "total = 0\nfor k in range(1, 4):\n    total = k\nprint(total)",
            "answer_key": "B",
            "explanation": "Two key rules apply here: (1) `range(1, 4)` produces `1, 2, 3` (stopping before 4), and (2) `total = k` overwrites `total` instead of adding (`total += k`). On the last iteration (`k = 3`), `total` is `3`.",
            "plain_language_explanation": "`range(1, 4)` counts 1, 2, 3 (it stops before 4). Inside the loop, `total = k` replaces `total` each time, so after the last step (`k = 3`), `total` is 3.",
            "worked_example": "# To sum 1 + 2 + 3 = 6:\ntotal = 0\nfor k in range(1, 4):\n    total += k  # 1, then 3, then 6",
            "diagram_svg": FLOWCHART_SVG_RANGE,
            "hint_ladder": [
                "First, which integers does `range(1, 4)` generate?",
                "Second, look at the loop body: does it say `total += k` or `total = k`?",
                "What is the final value of `k` in `range(1, 4)`?",
            ],
            "audio_transcript": "Audio transcript: Total starts at 0. For k in range(1, 4), the loop visits k=1, k=2, and k=3. Because the body says total = k, total ends with the last value of k, which is 3.",
            "options": [
                (
                    "A",
                    "4",
                    "MISC-LOOP-RANGE-STOP",
                    "MISC-LOOP-ACCUM-RESET",
                    0.52,
                    "Selecting 4 could result from thinking range(1, 4) includes 4 (with assignment `total = k`), OR from counting 4 iterations.",
                    False,
                ),
                ("B", "3", None, None, 1.0, None, True),
                (
                    "C",
                    "10",
                    "MISC-LOOP-RANGE-STOP",
                    None,
                    0.84,
                    None,
                    False,
                ),
                ("D", "6", "MISC-LOOP-ACCUM-RESET", None, 0.78, None, False),
            ],
        },
        {
            "stable_id": "PY-LOOP-FOLLOWUP-01",
            "concept_slug": "loops",
            "difficulty": 1,
            "is_verification_only": False,
            "is_diagnostic_followup": True,
            "target_misconception_codes": ["MISC-LOOP-RANGE-STOP", "MISC-LOOP-ACCUM-RESET"],
            "content": "[Diagnostic Follow-Up] To pinpoint what happened, which sequence of numbers does `list(range(2, 5))` produce in Python?",
            "code_snippet": "print(list(range(2, 5)))",
            "answer_key": "A",
            "explanation": "`range(2, 5)` starts at `2` (inclusive) and stops at `5` (exclusive), producing `[2, 3, 4]`.",
            "plain_language_explanation": "`range(2, 5)` starts at 2 and stops right before 5, giving `[2, 3, 4]`.",
            "worked_example": "list(range(0, 3)) -> [0, 1, 2]\nlist(range(2, 5)) -> [2, 3, 4]",
            "hint_ladder": [
                "Remember: in `range(start, stop)`, is `stop` included or excluded?",
            ],
            "options": [
                ("A", "[2, 3, 4]", None, None, 1.0, None, True),
                ("B", "[2, 3, 4, 5]", "MISC-LOOP-RANGE-STOP", None, 0.90, None, False),
                ("C", "[5]", "MISC-LOOP-ACCUM-RESET", None, 0.85, None, False),
                ("D", "[3, 4, 5]", None, None, 0.40, None, False),
            ],
        },
        {
            "stable_id": "PY-LOOP-VERIF-01",
            "concept_slug": "loops",
            "difficulty": 2,
            "is_verification_only": True,
            "is_diagnostic_followup": False,
            "content": "[Fresh Verification] What is the value of `result` after this loop completes?",
            "code_snippet": "result = 0\nfor n in range(2, 5):\n    result = result + n\nprint(result)",
            "answer_key": "B",
            "explanation": "`range(2, 5)` generates `2, 3, 4` (5 is excluded). Adding them into `result` gives `2 + 3 + 4 = 9`.",
            "plain_language_explanation": "`range(2, 5)` gives 2, 3, and 4. Adding `2 + 3 + 4` gives `9`.",
            "worked_example": "Iteration 1 (n=2): result = 0 + 2 = 2\nIteration 2 (n=3): result = 2 + 3 = 5\nIteration 3 (n=4): result = 5 + 4 = 9",
            "diagram_svg": FLOWCHART_SVG_RANGE,
            "hint_ladder": [
                "Which numbers are produced by `range(2, 5)`?",
                "Add each of those numbers into `result` step by step.",
            ],
            "options": [
                ("A", "14", "MISC-LOOP-RANGE-STOP", None, 0.86, None, False),
                ("B", "9", None, None, 1.0, None, True),
                ("C", "4", "MISC-LOOP-ACCUM-RESET", None, 0.84, None, False),
                ("D", "5", None, None, 0.40, None, False),
            ],
        },

        # --- CONCEPT 4: FUNCTIONS, PARAMETERS & RETURN (Includes Ambiguous Distractor + Follow-up) ---
        {
            "stable_id": "PY-FUNC-01",
            "concept_slug": "functions",
            "difficulty": 1,
            "is_verification_only": False,
            "is_diagnostic_followup": False,
            "content": "What is the value of `doubled` on line 4 after calling `show_double(6)`?",
            "code_snippet": "def show_double(x):\n    print(x * 2)\n\ndoubled = show_double(6)\nprint('doubled is:', doubled)",
            "answer_key": "C",
            "explanation": "`show_double(6)` prints `12` to the console, but because it has no `return` statement, Python automatically returns `None`. Therefore `doubled` is assigned `None`.",
            "plain_language_explanation": "`print(x * 2)` only shows `12` on the screen. Because the function does not have a `return` line, `doubled` receives `None`.",
            "worked_example": "def get_double(x):\n    return x * 2  # hands 12 back to caller\n\ndoubled = get_double(6)  # doubled is 12",
            "diagram_svg": FLOWCHART_SVG_FUNC_RETURN,
            "hint_ladder": [
                "Does `show_double(x)` contain a `return` statement anywhere?",
                "In Python, what value does a function return by default when it reaches the end without `return`?",
                "Distinguish what is printed inside the function from what is stored in `doubled`.",
            ],
            "audio_transcript": "Audio transcript: The function show_double prints x times 2, but has no return statement. Every Python function without an explicit return evaluates to None.",
            "options": [
                ("A", "12", "MISC-FUNC-PRINT-RETURN", None, 0.88, None, False),
                (
                    "B",
                    "6",
                    "MISC-FUNC-LOCAL-SCOPE",
                    "MISC-FUNC-PRINT-RETURN",
                    0.50,
                    "Selecting 6 could stem from confusing parameter value retention with missing return behavior.",
                    False,
                ),
                ("C", "None", None, None, 1.0, None, True),
                ("D", "NameError", None, None, 0.35, None, False),
            ],
        },
        {
            "stable_id": "PY-FUNC-FOLLOWUP-01",
            "concept_slug": "functions",
            "difficulty": 1,
            "is_verification_only": False,
            "is_diagnostic_followup": True,
            "target_misconception_codes": ["MISC-FUNC-PRINT-RETURN", "MISC-FUNC-LOCAL-SCOPE"],
            "content": "[Diagnostic Follow-Up] What does this code print on the final line?",
            "code_snippet": "def add_ten(n):\n    n = n + 10\n\nval = 5\nadd_ten(val)\nprint(val)",
            "answer_key": "A",
            "explanation": "`n` is a local parameter inside `add_ten`. Reassigning `n = n + 10` creates a new local integer `15` inside the function, leaving the outer variable `val` unchanged at `5`.",
            "plain_language_explanation": "Changing `n` inside `add_ten` only changes the local copy inside the function. Outside the function, `val` is still `5`.",
            "worked_example": "def add_ten(n):\n    return n + 10\nval = add_ten(5)  # Now val is 15",
            "hint_ladder": [
                "Is `n` inside `add_ten` a local variable or does it overwrite `val` outside?",
            ],
            "options": [
                ("A", "5", None, None, 1.0, None, True),
                ("B", "15", "MISC-FUNC-LOCAL-SCOPE", None, 0.90, None, False),
                ("C", "None", "MISC-FUNC-PRINT-RETURN", None, 0.85, None, False),
                ("D", "10", None, None, 0.35, None, False),
            ],
        },
        {
            "stable_id": "PY-FUNC-VERIF-01",
            "concept_slug": "functions",
            "difficulty": 2,
            "is_verification_only": True,
            "is_diagnostic_followup": False,
            "content": "[Fresh Verification] What happens when the final line `print(total + 5)` runs?",
            "code_snippet": "def compute_tax(amount):\n    print(amount * 0.10)\n\ntotal = compute_tax(100)\nprint(total + 5)",
            "answer_key": "D",
            "explanation": "Because `compute_tax` uses `print()` instead of `return`, `total` is `None`. Attempting `None + 5` raises a `TypeError`.",
            "plain_language_explanation": "`compute_tax` prints `10.0` but returns `None`. You cannot add `None + 5`, so Python raises a `TypeError`.",
            "worked_example": "def compute_tax(amount):\n    return amount * 0.10\n\ntotal = compute_tax(100)\nprint(total + 5)  # 15.0",
            "hint_ladder": [
                "What value is returned by `compute_tax(100)` and stored in `total`?",
                "Can Python add `None + 5`?",
            ],
            "options": [
                ("A", "15.0", "MISC-FUNC-PRINT-RETURN", None, 0.88, None, False),
                ("B", "105", "MISC-FUNC-LOCAL-SCOPE", None, 0.80, None, False),
                ("C", "None", None, None, 0.40, None, False),
                ("D", "TypeError (cannot add NoneType and int)", None, None, 1.0, None, True),
            ],
        },

        # --- CONCEPT 5: LISTS, INDEXING & MUTABILITY ---
        {
            "stable_id": "PY-LIST-01",
            "concept_slug": "lists",
            "difficulty": 1,
            "is_verification_only": False,
            "is_diagnostic_followup": False,
            "content": "What element is printed by `print(colors[1])`?",
            "code_snippet": "colors = ['teal', 'amber', 'indigo', 'coral']\nprint(colors[1])",
            "answer_key": "B",
            "explanation": "Python lists use 0-based indexing: `colors[0]` is `'teal'`, and `colors[1]` is the second item, `'amber'`.",
            "plain_language_explanation": "Python starts counting list positions at 0. Position 0 is `'teal'`, so position 1 is `'amber'`.",
            "worked_example": "colors[0] -> 'teal'\ncolors[1] -> 'amber'\ncolors[-1] -> 'coral'",
            "hint_ladder": [
                "What index number does Python use for the very first element of a list?",
                "If index 0 is `'teal'`, which element is at index 1?",
            ],
            "options": [
                ("A", "teal", "MISC-LIST-ZERO-INDEX", None, 0.88, None, False),
                ("B", "amber", None, None, 1.0, None, True),
                ("C", "indigo", None, None, 0.40, None, False),
                ("D", "coral", None, None, 0.40, None, False),
            ],
        },
        {
            "stable_id": "PY-LIST-02",
            "concept_slug": "lists",
            "difficulty": 2,
            "is_verification_only": False,
            "is_diagnostic_followup": False,
            "content": "What is printed by the code below?",
            "code_snippet": "scores = [40, 10, 30]\nscores = scores.sort()\nprint(scores)",
            "answer_key": "C",
            "explanation": "`scores.sort()` sorts the list in-place and returns `None`. Assigning `scores = scores.sort()` overwrites the variable `scores` with `None`!",
            "plain_language_explanation": "`.sort()` changes the list directly and returns `None`. Writing `scores = scores.sort()` replaces your list with `None`.",
            "worked_example": "# Either call .sort() without assignment:\nscores.sort()\n# Or use sorted() which returns a new list:\nscores = sorted(scores)",
            "hint_ladder": [
                "Does `list.sort()` return a new sorted list, or does it modify the list in-place and return `None`?",
                "What happens when you assign the return value of `scores.sort()` back to `scores`?",
            ],
            "options": [
                ("A", "[10, 30, 40]", "MISC-LIST-SORT-RETURN", None, 0.88, None, False),
                ("B", "[40, 10, 30]", None, None, 0.40, None, False),
                ("C", "None", None, None, 1.0, None, True),
                ("D", "[40, 30, 10]", None, None, 0.40, None, False),
            ],
        },
        {
            "stable_id": "PY-LIST-VERIF-01",
            "concept_slug": "lists",
            "difficulty": 2,
            "is_verification_only": True,
            "is_diagnostic_followup": False,
            "content": "[Fresh Verification] Given `cities = ['Delhi', 'Pune', 'Kochi']`, what does `cities[0]` evaluate to?",
            "code_snippet": "cities = ['Delhi', 'Pune', 'Kochi']\nprint(cities[0])",
            "answer_key": "A",
            "explanation": "Index `0` accesses the first element of the list, which is `'Delhi'`.",
            "plain_language_explanation": "Index 0 is always the first item in a Python list (`'Delhi'`).",
            "worked_example": "cities[0] -> 'Delhi'\ncities[1] -> 'Pune'",
            "hint_ladder": [
                "Recall zero-based indexing: index 0 refers to which position?",
            ],
            "options": [
                ("A", "Delhi", None, None, 1.0, None, True),
                ("B", "Pune", "MISC-LIST-ZERO-INDEX", None, 0.88, None, False),
                ("C", "IndexError", None, None, 0.35, None, False),
                ("D", "None", "MISC-LIST-SORT-RETURN", None, 0.75, None, False),
            ],
        },

        # --- CONCEPT 6: LIST ITERATION & FILTERING ---
        {
            "stable_id": "PY-ITER-01",
            "concept_slug": "list-iteration",
            "difficulty": 2,
            "is_verification_only": False,
            "is_diagnostic_followup": False,
            "content": "Why does the following loop raise an `IndexError: list index out of range`?",
            "code_snippet": "nums = [10, 20, 30]\nfor x in nums:\n    print(nums[x])",
            "answer_key": "A",
            "explanation": "In `for x in nums:`, `x` takes the element values `10`, `20`, `30`—not the indices `0`, `1`, `2`. Trying to access `nums[10]` on a 3-element list raises `IndexError`.",
            "plain_language_explanation": "`for x in nums:` gives you the numbers inside the list (`10, 20, 30`), not their positions (`0, 1, 2`). Asking for `nums[10]` fails because the list only has 3 items.",
            "worked_example": "# Direct element iteration:\nfor x in nums:\n    print(x)\n# Or index + value with enumerate:\nfor i, x in enumerate(nums):\n    print(i, x)",
            "hint_ladder": [
                "On the first iteration of `for x in [10, 20, 30]:`, what is the value of `x`?",
                "If `x` is `10`, what does `nums[10]` try to look up?",
            ],
            "options": [
                ("A", "Because `x` is the element value (10), not the index (0), so `nums[10]` is out of range", None, None, 1.0, None, True),
                ("B", "Because Python lists cannot be printed inside a for loop", "MISC-ITER-INDEX-VALUE", None, 0.86, None, False),
                ("C", "Because `nums` starts at index 1", "MISC-LIST-ZERO-INDEX", None, 0.78, None, False),
                ("D", "Because `for` loops only work with `range()`", "MISC-ITER-INDEX-VALUE", None, 0.82, None, False),
            ],
        },
        {
            "stable_id": "PY-ITER-VERIF-01",
            "concept_slug": "list-iteration",
            "difficulty": 2,
            "is_verification_only": True,
            "is_diagnostic_followup": False,
            "content": "[Fresh Verification] What does the following code print?",
            "code_snippet": "values = [5, 12, 8, 15]\ncount = 0\nfor v in values:\n    if v >= 10:\n        count += 1\nprint(count)",
            "answer_key": "B",
            "explanation": "The loop visits each value `v` directly (`5, 12, 8, 15`) and increments `count` when `v >= 10` (`12` and `15`), resulting in `2`.",
            "plain_language_explanation": "Two numbers in `[5, 12, 8, 15]` are 10 or greater (`12` and `15`), so `count` becomes `2`.",
            "worked_example": "v=5 (skip) -> v=12 (count=1) -> v=8 (skip) -> v=15 (count=2)",
            "hint_ladder": [
                "Check each item in `[5, 12, 8, 15]`: how many are `>= 10`?",
            ],
            "options": [
                ("A", "27", "MISC-ITER-INDEX-VALUE", None, 0.80, None, False),
                ("B", "2", None, None, 1.0, None, True),
                ("C", "4", "MISC-ITER-FILTER-INDENT", None, 0.82, None, False),
                ("D", "1", None, None, 0.40, None, False),
            ],
        },
    ]

    question_objs: dict[str, Question] = {}
    for qd in questions_data:
        q = Question(
            stable_id=qd["stable_id"],
            concept_id=concept_objs[qd["concept_slug"]].id,
            difficulty=qd["difficulty"],
            question_type="multiple_choice",
            is_verification_only=qd["is_verification_only"],
            is_diagnostic_followup=qd["is_diagnostic_followup"],
            target_misconception_codes=qd.get("target_misconception_codes", []),
            content=qd["content"],
            code_snippet=qd["code_snippet"],
            answer_key=qd["answer_key"],
            explanation=qd["explanation"],
            plain_language_explanation=qd.get("plain_language_explanation"),
            worked_example=qd.get("worked_example"),
            hint_ladder=qd.get("hint_ladder", []),
            diagram_svg=qd.get("diagram_svg"),
            audio_transcript=qd.get("audio_transcript"),
            version="1.0.0",
            status="published",
        )
        db.add(q)
        db.flush()
        question_objs[q.stable_id] = q

        for opt_key, opt_text, m1_code, m2_code, conf_w, amb_note, is_corr in qd["options"]:
            db.add(
                AnswerOption(
                    question_id=q.id,
                    option_key=opt_key,
                    option_text=opt_text,
                    misconception_id=misc_objs[m1_code].id if m1_code else None,
                    secondary_misconception_id=misc_objs[m2_code].id if m2_code else None,
                    confidence_weight=conf_w,
                    ambiguity_note=amb_note,
                    is_correct=is_corr,
                )
            )
    db.flush()

    # 6. Curated Multimodal Remediation Activities
    activities_data = [
        {
            "stable_id": "ACT-VAR-01",
            "concept_slug": "variables-expressions",
            "target_misc_code": "MISC-VAR-REASSIGN",
            "title": "Visualizing Variable Binding & Sequential Reassignment",
            "activity_type": "targeted_remediation",
            "difficulty": 1,
            "content_ref": "PSM147-PY-MOD1-A1",
            "content_body": (
                "In Python, `=` is an assignment statement, not a permanent algebraic equation. "
                "When `total = price + 5` executes, Python evaluates `price + 5` right then and binds "
                "the resulting object (`15`) to `total`. Rebinding `price` on a later line points `price` "
                "to a new number without altering `total`."
            ),
            "plain_language_body": (
                "Think of a variable like a sticky note attached to a value. When you calculate `total = price + 5`, "
                "Python writes down the result (`15`) and attaches the `total` label to `15`. Moving the `price` "
                "label later does not change `total`."
            ),
            "code_example": "a = 10\nb = a + 5   # b is bound to 15\na = 99      # a is rebound to 99; b is still 15\nprint(a, b) # Output: 99 15",
            "audio_transcript": "Narration transcript: In Python, assignment binds a variable name to the current value of an expression. Changing one variable later does not automatically recalculate earlier variables.",
            "interactive_exercise": {
                "prompt": "Quick Check: If `x = 4`, then `y = x + 1`, and then `x = 10`, what is `y`?",
                "expected_answer": "5",
                "hint": "`y` was calculated when `x` was still 4.",
            },
            "format": "multimodal",
            "estimated_duration": 5,
        },
        {
            "stable_id": "ACT-COND-01",
            "concept_slug": "conditions",
            "target_misc_code": "MISC-COND-ELIF-CHAIN",
            "title": "Interactive Walkthrough: Mutually Exclusive if/elif vs. Separate if Blocks",
            "activity_type": "visual_walkthrough",
            "difficulty": 1,
            "content_ref": "PSM147-PY-MOD2-A1",
            "content_body": (
                "When two conditions can both be true (for example, `score >= 80` and `score >= 60` when `score = 85`), "
                "using two separate `if` statements causes BOTH blocks to run in sequence. Using `if ... elif ...` links "
                "them into a single decision structure where only the FIRST matching branch runs."
            ),
            "plain_language_body": (
                "Use `elif` when you only want one branch to win. If you write a second `if` instead of `elif`, "
                "Python treats it as a brand-new question and runs it too."
            ),
            "code_example": "score = 85\nif score >= 80:\n    grade = 'A'\nelif score >= 60:\n    grade = 'B'  # Skipped because the first branch already matched!\nprint(grade)     # Output: A",
            "diagram_svg": FLOWCHART_SVG_IF_ELIF,
            "audio_transcript": "Narration transcript: In an if-elif chain, Python stops testing conditions as soon as the first True branch executes. In separate if statements, every condition is tested independently.",
            "interactive_exercise": {
                "prompt": "Quick Check: Which keyword links a second branch so it only runs when the first `if` was False?",
                "expected_answer": "elif",
                "hint": "It is short for 'else if' in Python.",
            },
            "format": "multimodal",
            "estimated_duration": 6,
        },
        {
            "stable_id": "ACT-LOOP-01",
            "concept_slug": "loops",
            "target_misc_code": "MISC-LOOP-RANGE-STOP",
            "title": "Tracing range(start, stop) Stopping Conditions & Accumulators",
            "activity_type": "targeted_remediation",
            "difficulty": 1,
            "content_ref": "PSM147-PY-MOD3-A1",
            "content_body": (
                "Python's `range(start, stop)` uses a half-open interval `[start, stop)`: it begins at `start` "
                "and stops strictly BEFORE `stop`. To accumulate a sum across iterations, initialize `total = 0` "
                "before the loop and use `total += k` inside the loop body."
            ),
            "plain_language_body": (
                "`range(1, 4)` counts 1, 2, 3 and stops before 4. Also, use `total += k` to add to `total` instead of `total = k` which erases the previous sum."
            ),
            "code_example": "total = 0\nfor k in range(1, 4):  # visits k = 1, 2, 3\n    total += k         # 0+1=1 -> 1+2=3 -> 3+3=6\nprint(total)           # Output: 6",
            "diagram_svg": FLOWCHART_SVG_RANGE,
            "audio_transcript": "Narration transcript: range of 1 comma 4 generates 1, 2, and 3. The upper bound 4 is the stopping point and is never included in the loop.",
            "interactive_exercise": {
                "prompt": "Quick Check: What is the LAST integer generated by `range(3, 7)`?",
                "expected_answer": "6",
                "hint": "It stops one integer before 7.",
            },
            "format": "multimodal",
            "estimated_duration": 6,
        },
        {
            "stable_id": "ACT-FUNC-01",
            "concept_slug": "functions",
            "target_misc_code": "MISC-FUNC-PRINT-RETURN",
            "title": "Understanding Function Return Values vs. Console print() Side Effects",
            "activity_type": "worked_example",
            "difficulty": 1,
            "content_ref": "PSM147-PY-MOD4-A1",
            "content_body": (
                "Calling `print()` inside a function only displays characters on the terminal; it does not send "
                "a value back to the expression that called the function. To store or reuse a function's result "
                "in a variable (`ans = double(6)`), the function must execute `return x * 2`."
            ),
            "plain_language_body": (
                "`print()` is only for human eyes on the screen. `return` actually hands the answer back to your program so you can save it in a variable."
            ),
            "code_example": "def area(w, h):\n    return w * h\n\nroom = area(4, 5) + 10\nprint(room)  # Output: 30",
            "diagram_svg": FLOWCHART_SVG_FUNC_RETURN,
            "audio_transcript": "Narration transcript: A function without a return statement returns None. Use return whenever the caller needs to store or compute with the result.",
            "interactive_exercise": {
                "prompt": "Quick Check: What value does a Python function return if it has no `return` statement?",
                "expected_answer": "None",
                "hint": "It is Python's special null value, capitalized.",
            },
            "format": "multimodal",
            "estimated_duration": 5,
        },
        {
            "stable_id": "ACT-LIST-01",
            "concept_slug": "lists",
            "target_misc_code": "MISC-LIST-ZERO-INDEX",
            "title": "Zero-Based List Indexing & In-Place List Methods",
            "activity_type": "interactive_practice",
            "difficulty": 1,
            "content_ref": "PSM147-PY-MOD5-A1",
            "content_body": (
                "Python indices represent the offset from the start of the list: the first item is at offset `0` (`items[0]`), "
                "and the second is at offset `1` (`items[1]`). Additionally, mutating methods like `items.append(x)` "
                "and `items.sort()` modify the list in-place and return `None`."
            ),
            "plain_language_body": (
                "Always start counting list positions from 0: position 0 is first, position 1 is second. And remember `items.sort()` sorts the list directly without returning a copy."
            ),
            "code_example": "fruits = ['apple', 'mango', 'banana']\nprint(fruits[0])  # 'apple' (first)\nprint(fruits[1])  # 'mango' (second)\nfruits.sort()     # sorts in-place\nprint(fruits)     # ['apple', 'banana', 'mango']",
            "audio_transcript": "Narration transcript: Zero-based indexing means index 0 is the first element and index 1 is the second element.",
            "interactive_exercise": {
                "prompt": "Quick Check: In `nums = [100, 200, 300]`, what index holds `100`?",
                "expected_answer": "0",
                "hint": "First element offset is zero.",
            },
            "format": "multimodal",
            "estimated_duration": 5,
        },
        {
            "stable_id": "ACT-ITER-01",
            "concept_slug": "list-iteration",
            "target_misc_code": "MISC-ITER-INDEX-VALUE",
            "title": "Iterating Directly Over List Elements vs. Using Indices",
            "activity_type": "targeted_remediation",
            "difficulty": 2,
            "content_ref": "PSM147-PY-MOD6-A1",
            "content_body": (
                "When you write `for item in my_list:`, Python assigns each element's value directly to `item` on every pass. "
                "You do not need `my_list[item]`. If you need both the position index and the value, use `for idx, item in enumerate(my_list):`."
            ),
            "plain_language_body": (
                "In `for x in nums:`, `x` is already the number inside the list—not its index position. Just use `x` directly!"
            ),
            "code_example": "prices = [120, 250, 80]\nhigh_prices = []\nfor p in prices:\n    if p >= 100:\n        high_prices.append(p)\nprint(high_prices)  # [120, 250]",
            "audio_transcript": "Narration transcript: In a Python for-in loop over a list, the loop variable holds the element value itself, not its index.",
            "interactive_exercise": {
                "prompt": "Quick Check: Which built-in function gives both `(index, value)` pairs when looping over a list?",
                "expected_answer": "enumerate",
                "hint": "Starts with 'enum...'",
            },
            "format": "multimodal",
            "estimated_duration": 6,
        },
    ]

    activity_objs: dict[str, Activity] = {}
    for ad in activities_data:
        act = Activity(
            stable_id=ad["stable_id"],
            concept_id=concept_objs[ad["concept_slug"]].id,
            target_misconception_id=(
                misc_objs[ad["target_misc_code"]].id
                if ad.get("target_misc_code")
                else None
            ),
            title=ad["title"],
            activity_type=ad["activity_type"],
            difficulty=ad["difficulty"],
            content_ref=ad["content_ref"],
            content_body=ad["content_body"],
            plain_language_body=ad["plain_language_body"],
            code_example=ad["code_example"],
            diagram_svg=ad.get("diagram_svg"),
            audio_transcript=ad.get("audio_transcript"),
            interactive_exercise=ad.get("interactive_exercise"),
            format=ad["format"],
            estimated_duration=ad["estimated_duration"],
            version="1.0.0",
            status="published",
        )
        db.add(act)
        db.flush()
        activity_objs[act.stable_id] = act

    # 7. Achievements / Milestones (Non-punitive gamification)
    achievements_spec = [
        (
            "FIRST_ATTEMPT",
            "First Diagnostic Step",
            "Completed your first Python practice question and inspected the feedback.",
            "milestone",
            20,
            {"type": "attempts_count", "threshold": 1},
        ),
        (
            "ACTIVE_PRACTICE_5",
            "Consistent Problem Solver",
            "Completed 5 question attempts across the Python concept map.",
            "milestone",
            35,
            {"type": "attempts_count", "threshold": 5},
        ),
        (
            "VERIFIED_REMEDIATION_1",
            "Close the Gap",
            "Completed a targeted remediation activity and verified understanding with a fresh follow-up question.",
            "remediation",
            50,
            {"type": "verified_interventions", "threshold": 1},
        ),
        (
            "CONCEPT_BUILDER_2",
            "Concept Builder",
            "Reached strong recent evidence (>= 70% mastery estimate) in at least 2 Python concepts.",
            "mastery",
            60,
            {"type": "strong_concepts", "threshold": 2},
        ),
    ]
    for code, name, desc, cat, pts, crit in achievements_spec:
        db.add(
            Achievement(
                code=code,
                name=name,
                description=desc,
                category=cat,
                points_reward=pts,
                criteria=crit,
            )
        )
    db.flush()

    # 8. Seed Demo Users (Student, Cohort Students, Educator, Admin)
    aarav = User(
        email="aarav.student@demo.learnwhy.edu",
        full_name="Aarav Sharma (Demo Student)",
        password_hash=hash_password("StudentPass123!"),
        role="student",
        status="active",
        onboarding_completed=True,
        selected_course_id=course.id,
        points=85,
        current_streak=3,
        daily_goal_minutes=20,
        streak_opt_in=True,
    )
    priya = User(
        email="priya.student@demo.learnwhy.edu",
        full_name="Priya Nair (Demo Student)",
        password_hash=hash_password("StudentPass123!"),
        role="student",
        status="active",
        onboarding_completed=True,
        selected_course_id=course.id,
        points=45,
        current_streak=2,
        daily_goal_minutes=15,
        streak_opt_in=True,
    )
    rohan = User(
        email="rohan.student@demo.learnwhy.edu",
        full_name="Rohan Verma (Demo Student)",
        password_hash=hash_password("StudentPass123!"),
        role="student",
        status="active",
        onboarding_completed=True,
        selected_course_id=course.id,
        points=110,
        current_streak=4,
        daily_goal_minutes=25,
        streak_opt_in=True,
    )
    educator = User(
        email="meera.educator@demo.learnwhy.edu",
        full_name="Prof. Meera Krishnan (Demo Educator)",
        password_hash=hash_password("EducatorPass123!"),
        role="educator",
        status="active",
        onboarding_completed=True,
        selected_course_id=course.id,
    )
    admin = User(
        email="vikram.admin@demo.learnwhy.edu",
        full_name="Vikram Desai (Demo Admin)",
        password_hash=hash_password("AdminPass123!"),
        role="admin",
        status="active",
        onboarding_completed=True,
        selected_course_id=course.id,
    )
    db.add_all([aarav, priya, rohan, educator, admin])
    db.flush()

    for u in [aarav, priya, rohan, educator, admin]:
        db.add(
            LearnerPreference(
                user_id=u.id,
                language="en",
                text_size="normal",
                reduced_motion=False,
                high_contrast=False,
                plain_language_mode=False,
                preferred_formats=["text", "diagram", "interactive", "audio"],
            )
        )
    db.flush()

    # Initialize mastery states for students
    for stu in [aarav, priya, rohan]:
        for c in concept_objs.values():
            get_or_create_mastery_state(db, stu.id, c)
    db.flush()

    # 9. Record realistic sample attempts, diagnoses, and intervention outcomes for cohort
    # Aarav: strong in variables, had a misconception in loops that was remediated & verified, currently practicing conditions/functions
    sample_attempt_specs = [
        (aarav, "PY-VAR-01", "B", True, "practice"),
        (aarav, "PY-VAR-02", "C", True, "practice"),
        (aarav, "PY-COND-01", "A", False, "practice"),
        (aarav, "PY-LOOP-01", "C", False, "practice"),
        # Priya: struggling with loops & functions (flagged for supportive educator review)
        (priya, "PY-VAR-01", "A", False, "practice"),
        (priya, "PY-LOOP-01", "C", False, "practice"),
        (priya, "PY-LOOP-VERIF-01", "A", False, "practice"),
        (priya, "PY-FUNC-01", "A", False, "practice"),
        # Rohan: strong across variables & conditions, minor slip in lists
        (rohan, "PY-VAR-01", "B", True, "practice"),
        (rohan, "PY-COND-01", "C", True, "practice"),
        (rohan, "PY-LIST-01", "A", False, "practice"),
    ]

    last_aarav_loop_attempt = None
    last_aarav_loop_diag = None
    for stu, q_sid, resp, is_corr, ctx in sample_attempt_specs:
        q_obj = question_objs[q_sid]
        c_obj = next(c for c in concept_objs.values() if c.id == q_obj.concept_id)
        att = Attempt(
            user_id=stu.id,
            question_id=q_obj.id,
            response=resp,
            is_correct=is_corr,
            hints_used=1 if not is_corr else 0,
            attempt_context=ctx,
        )
        db.add(att)
        db.flush()
        update_concept_mastery(db, stu.id, c_obj, is_corr, context_note=f"seed sample {q_sid}")
        diag = diagnose_attempt(db, att, q_obj)
        if stu.id == aarav.id and q_sid == "PY-LOOP-01":
            last_aarav_loop_attempt = att
            last_aarav_loop_diag = diag

    # Seed one completed + verified intervention outcome for Aarav on Loops
    loop_rec = Recommendation(
        user_id=aarav.id,
        activity_id=activity_objs["ACT-LOOP-01"].id,
        concept_id=concept_objs["loops"].id,
        trigger_attempt_id=last_aarav_loop_attempt.id if last_aarav_loop_attempt else None,
        trigger_diagnosis_id=last_aarav_loop_diag.id if last_aarav_loop_diag else None,
        strategy="proposed",
        total_score=0.84,
        score_components={
            "gap_relevance": 0.82,
            "prerequisite_importance": 0.85,
            "difficulty_fit": 0.88,
            "weights": {"gap_relevance": 0.5, "prerequisite_importance": 0.3, "difficulty_fit": 0.2},
            "formula": "R = 0.50*gap_relevance + 0.30*prerequisite_importance + 0.20*difficulty_fit",
            "targets_diagnosed_misconception": True,
        },
        reason=(
            "Recommended because your recent responses indicate a possible misconception on "
            "'Off-by-one error: assuming range(start, stop) includes stop' in Loops & Stopping Conditions."
        ),
        rank=1,
        status="verified",
        rule_version="v1.0.0-rules",
    )
    db.add(loop_rec)
    db.flush()

    verif_q = question_objs["PY-LOOP-VERIF-01"]
    verif_att = Attempt(
        user_id=aarav.id,
        question_id=verif_q.id,
        response="B",
        is_correct=True,
        hints_used=0,
        attempt_context="verification",
    )
    db.add(verif_att)
    db.flush()
    pre_m, post_ms = update_concept_mastery(
        db, aarav.id, concept_objs["loops"], True, context_note="seed verification PY-LOOP-VERIF-01"
    )
    db.add(
        InterventionOutcome(
            recommendation_id=loop_rec.id,
            user_id=aarav.id,
            concept_id=concept_objs["loops"].id,
            pre_attempt_id=last_aarav_loop_attempt.id if last_aarav_loop_attempt else None,
            followup_attempt_id=verif_att.id,
            verification_question_id=verif_q.id,
            pre_mastery=pre_m,
            post_mastery=post_ms.mastery,
            immediate_outcome="improved",
            error_recurred=False,
            original_misconception_id=misc_objs["MISC-LOOP-RANGE-STOP"].id,
            post_misconception_id=None,
            completion_seconds=145,
            educator_note="Sample review note: Learner resolved range() upper-bound misconception on immediate verification.",
            educator_Acknowledged=True,
            rule_version="v1.0.0-rules",
        )
    )

    # Generate initial pending recommendations for Aarav and Priya
    generate_recommendations_for_user(db, aarav.id, strategy="proposed", limit=4)
    generate_recommendations_for_user(db, priya.id, strategy="proposed", limit=4)

    # Award initial badge to Aarav
    first_ach = db.query(Achievement).filter(Achievement.code == "FIRST_ATTEMPT").first()
    verif_ach = db.query(Achievement).filter(Achievement.code == "VERIFIED_REMEDIATION_1").first()
    if first_ach:
        db.add(UserAchievement(user_id=aarav.id, achievement_id=first_ach.id))
    if verif_ach:
        db.add(UserAchievement(user_id=aarav.id, achievement_id=verif_ach.id))

    log_audit_event(
        db,
        action="seed_data_initialized",
        entity_type="system",
        entity_id="python-foundations-101",
        actor_role="system",
        metadata={
            "note": "Initialized sample demo data (explicitly labeled as sample data).",
            "concepts_count": len(concept_objs),
            "questions_count": len(question_objs),
            "misconceptions_count": len(misc_objs),
            "activities_count": len(activity_objs),
        },
    )
    db.commit()


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        seed_database(session)
    print("LearnWhy AI database seeded successfully.")

import logging

from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    jwt_required,
    get_jwt_identity,
    get_jwt
)

from database.db import db

from models.cms import (
    Lecture,
    Test,
    Question,
    TestSubmission
)

from models.academic_record import AcademicRecord
from models.user import User
from models.prediction import Prediction

from utils.decorators import role_required

from routes.prediction import (
    calculate_dummy_score,
    get_performance_category
)


logger = logging.getLogger(__name__)

cms_bp = Blueprint("cms", __name__)


# ============================================================
# LECTURES
# ============================================================

@cms_bp.route("/lectures", methods=["GET"])
@jwt_required()
def get_lectures():
    """Students, faculty and admin can view lectures."""

    lectures = (
        Lecture.query
        .order_by(Lecture.created_at.desc())
        .all()
    )

    return jsonify({
        "status": "success",
        "data": [lecture.to_dict() for lecture in lectures]
    }), 200


@cms_bp.route("/lectures", methods=["POST"])
@jwt_required()
@role_required("faculty", "admin")
def create_lecture():
    """Faculty/Admin can create a lecture."""

    data = request.get_json(silent=True) or {}

    title = str(data.get("title", "")).strip()
    link = str(data.get("link", "")).strip()

    if not title or not link:
        return jsonify({
            "status": "error",
            "error": "Title and link are required"
        }), 400

    lecture = Lecture(
        title=title,
        description=data.get("description", ""),
        link=link,
        faculty_id=int(get_jwt_identity())
    )

    try:
        db.session.add(lecture)
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Lecture created successfully",
            "data": lecture.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(
            f"Error creating lecture: {e}",
            exc_info=True
        )

        return jsonify({
            "status": "error",
            "error": "Unable to create lecture"
        }), 500


@cms_bp.route("/lectures/<int:lecture_id>", methods=["DELETE"])
@jwt_required()
@role_required("faculty", "admin")
def delete_lecture(lecture_id):
    """Faculty/Admin can delete lecture."""

    lecture = Lecture.query.get_or_404(lecture_id)

    try:
        db.session.delete(lecture)
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Lecture deleted successfully"
        }), 200

    except Exception as e:
        db.session.rollback()

        logger.error(
            f"Error deleting lecture: {e}",
            exc_info=True
        )

        return jsonify({
            "status": "error",
            "error": "Unable to delete lecture"
        }), 500


# ============================================================
# TESTS
# ============================================================

@cms_bp.route("/tests", methods=["GET"])
@jwt_required()
def get_tests():
    """Get all tests with their questions."""
    tests = Test.query.order_by(Test.created_at.desc()).all()

    role = get_jwt().get("role", "student").lower()
    include_answer = role in ["faculty", "admin"]

    return jsonify({
        "status": "success",
        "data": [
            {
                **t.to_dict(),
                "questions": [
                    q.to_dict(include_answer=include_answer)
                    for q in t.questions
                ]
            }
            for t in tests
        ]
    }), 200

# ============================================================
# CREATE TEST
# ============================================================

@cms_bp.route("/tests", methods=["POST"])
@jwt_required()
@role_required("faculty", "admin")
def create_test():
    """Faculty/Admin creates test with MCQ questions."""

    data = request.get_json(silent=True) or {}

    title = str(data.get("title", "")).strip()
    description = data.get("description", "")
    questions_data = data.get("questions", [])

    if not title:
        return jsonify({
            "status": "error",
            "error": "Test title is required"
        }), 400

    if not isinstance(questions_data, list) or not questions_data:
        return jsonify({
            "status": "error",
            "error": "At least one question is required"
        }), 400

    # Validate all questions BEFORE database insertion
    validated_questions = []

    for index, q_data in enumerate(questions_data, start=1):

        if not isinstance(q_data, dict):
            return jsonify({
                "status": "error",
                "error": f"Question {index} is invalid"
            }), 400

        question_text = str(
            q_data.get("question_text", "")
        ).strip()

        options = q_data.get("options", {})

        if not question_text:
            return jsonify({
                "status": "error",
                "error": f"Question {index} text is required"
            }), 400

        if not isinstance(options, dict):
            return jsonify({
                "status": "error",
                "error": f"Options for question {index} are invalid"
            }), 400

        for option in ["A", "B", "C", "D"]:
            if not str(options.get(option, "")).strip():
                return jsonify({
                    "status": "error",
                    "error": (
                        f"Option {option} is required "
                        f"for question {index}"
                    )
                }), 400

        correct_option = str(
            q_data.get("correct_option", "")
        ).upper().strip()

        if correct_option not in ["A", "B", "C", "D"]:
            return jsonify({
                "status": "error",
                "error": (
                    f"Correct option for question {index} "
                    f"must be A, B, C or D"
                )
            }), 400

        validated_questions.append({
            "question_text": question_text,
            "option_a": str(options["A"]).strip(),
            "option_b": str(options["B"]).strip(),
            "option_c": str(options["C"]).strip(),
            "option_d": str(options["D"]).strip(),
            "correct_option": correct_option
        })

    # Duration
    duration_minutes = None

    if data.get("duration_minutes") not in [
        None,
        "",
        "null"
    ]:
        try:
            duration_minutes = int(
                data.get("duration_minutes")
            )

            if duration_minutes <= 0:
                raise ValueError

        except (ValueError, TypeError):
            return jsonify({
                "status": "error",
                "error": "Duration must be a positive number"
            }), 400

    try:

        test = Test(
            title=title,
            description=description,
            faculty_id=int(get_jwt_identity()),
            duration_minutes=duration_minutes
        )

        db.session.add(test)
        db.session.flush()

        for q in validated_questions:

            question = Question(
                test_id=test.id,
                question_text=q["question_text"],
                option_a=q["option_a"],
                option_b=q["option_b"],
                option_c=q["option_c"],
                option_d=q["option_d"],
                correct_option=q["correct_option"]
            )

            db.session.add(question)

        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Test created successfully",
            "data": test.to_dict()
        }), 201

    except Exception as e:

        db.session.rollback()

        logger.error(
            f"Error creating test: {e}",
            exc_info=True
        )

        return jsonify({
            "status": "error",
            "error": "Unable to create test"
        }), 500


# ============================================================
# TEST DETAILS
# ============================================================

@cms_bp.route("/tests/<int:test_id>", methods=["GET"])
@jwt_required()
def get_test_details(test_id):
    """
    Get test details.

    Student:
        questions WITHOUT correct answers.

    Faculty/Admin:
        questions WITH correct answers.
    """

    test = Test.query.get_or_404(test_id)

    role = get_jwt().get("role", "").lower()

    include_answer = role in [
        "faculty",
        "admin"
    ]

    result = test.to_dict()

    result["questions"] = [
        question.to_dict(
            include_answer=include_answer
        )
        for question in test.questions
    ]

    # Student attempt status
    if role == "student":

        user_id = int(get_jwt_identity())

        previous_submission = TestSubmission.query.filter_by(
            test_id=test.id,
            user_id=user_id
        ).first()

        result["already_attempted"] = (
            previous_submission is not None
        )

        if previous_submission:
            result["submission"] = (
                previous_submission.to_dict()
            )

    return jsonify({
        "status": "success",
        "data": result
    }), 200


# ============================================================
# DELETE TEST
# ============================================================

@cms_bp.route("/tests/<int:test_id>", methods=["DELETE"])
@jwt_required()
@role_required("faculty", "admin")
def delete_test(test_id):
    """
    Delete test.

    Questions are automatically deleted because
    Test.questions relationship uses cascade
    delete-orphan.

    Student submissions are deleted first.
    """

    test = Test.query.get_or_404(test_id)

    try:

        # Delete submissions first
        TestSubmission.query.filter_by(
            test_id=test.id
        ).delete(
            synchronize_session=False
        )

        # Test delete
        # Questions will be deleted through relationship cascade
        db.session.delete(test)

        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Test and its questions deleted successfully"
        }), 200

    except Exception as e:

        db.session.rollback()

        logger.error(
            f"Error deleting test: {e}",
            exc_info=True
        )

        return jsonify({
            "status": "error",
            "error": "Unable to delete test"
        }), 500


# ============================================================
# SUBMIT TEST
# ============================================================

@cms_bp.route(
    "/tests/<int:test_id>/submit",
    methods=["POST"]
)
@jwt_required()
@role_required("student")
def submit_test(test_id):
    """
    Student submits test.

    IMPORTANT:
    One student can submit one test ONLY ONCE.
    """

    test = Test.query.get_or_404(test_id)

    user_id = int(get_jwt_identity())

    # Check duplicate submission
    existing_submission = TestSubmission.query.filter_by(
        test_id=test.id,
        user_id=user_id
    ).first()

    if existing_submission:

        return jsonify({
            "status": "error",
            "error": "You have already attempted this test.",
            "already_attempted": True,
            "data": existing_submission.to_dict()
        }), 409

    data = request.get_json(silent=True) or {}

    answers = data.get("answers", {})

    if not isinstance(answers, dict):
        return jsonify({
            "status": "error",
            "error": "Answers must be an object"
        }), 400

    correct = 0
    total = len(test.questions)

    for question in test.questions:

        user_answer = str(
            answers.get(str(question.id), "")
        ).upper().strip()

        correct_answer = str(
            question.correct_option
        ).upper().strip()

        if user_answer == correct_answer:
            correct += 1

    submission = TestSubmission(
        test_id=test.id,
        user_id=user_id,
        score=correct,
        total_questions=total,
        is_faculty_overridden=False
    )

    try:

        db.session.add(submission)
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Test submitted successfully",
            "data": submission.to_dict()
        }), 200

    except Exception as e:

        db.session.rollback()

        logger.error(
            f"Error submitting test: {e}",
            exc_info=True
        )

        return jsonify({
            "status": "error",
            "error": "Unable to submit test"
        }), 500


# ============================================================
# STUDENT TEST SUBMISSIONS
# ============================================================

@cms_bp.route(
    "/student/<int:student_id>/test-submissions",
    methods=["GET"]
)
@jwt_required()
@role_required("faculty", "admin")
def get_student_test_submissions(student_id):
    """
    Faculty/Admin can view all test submissions
    of a particular student.
    """

    student = User.query.filter_by(
        id=student_id,
        role="student"
    ).first_or_404()

    submissions = (
        TestSubmission.query
        .filter_by(user_id=student.id)
        .order_by(TestSubmission.submitted_at.desc())
        .all()
    )

    result = []

    for submission in submissions:

        percentage = 0

        if submission.total_questions:
            percentage = round(
                (
                    submission.score /
                    submission.total_questions
                ) * 100,
                2
            )

        result.append({
            "id": submission.id,
            "test_id": submission.test_id,
            "test_title": (
                submission.test.title
                if submission.test
                else "Unknown Test"
            ),
            "user_id": submission.user_id,
            "score": submission.score,
            "total_questions": submission.total_questions,
            "percentage": percentage,
            "is_faculty_overridden": (
                submission.is_faculty_overridden
            ),
            "submitted_at": (
                submission.submitted_at.isoformat()
                if submission.submitted_at
                else None
            )
        })

    return jsonify({
        "status": "success",
        "data": result
    }), 200


# ============================================================
# FACULTY SCORE OVERRIDE
# ============================================================

@cms_bp.route(
    "/student/<int:student_id>/test/<int:submission_id>",
    methods=["PUT"]
)
@jwt_required()
@role_required("faculty", "admin")
def override_test_score(
    student_id,
    submission_id
):
    """Faculty/Admin manually updates test score."""

    submission = TestSubmission.query.filter_by(
        id=submission_id,
        user_id=student_id
    ).first_or_404()

    data = request.get_json(silent=True) or {}

    if "score" not in data:
        return jsonify({
            "status": "error",
            "error": "Score is required"
        }), 400

    try:

        new_score = float(data["score"])

    except (ValueError, TypeError):

        return jsonify({
            "status": "error",
            "error": "Score must be a number"
        }), 400

    if new_score < 0:
        return jsonify({
            "status": "error",
            "error": "Score cannot be negative"
        }), 400

    if new_score > submission.total_questions:
        return jsonify({
            "status": "error",
            "error": (
                "Score cannot be greater than "
                "total questions"
            )
        }), 400

    submission.score = new_score
    submission.is_faculty_overridden = True

    try:

        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Student score updated successfully",
            "data": submission.to_dict()
        }), 200

    except Exception as e:

        db.session.rollback()

        logger.error(
            f"Error overriding score: {e}",
            exc_info=True
        )

        return jsonify({
            "status": "error",
            "error": "Unable to update score"
        }), 500


# ============================================================
# ACADEMIC RECORD OVERRIDE
# ============================================================

@cms_bp.route(
    "/student/<int:student_id>/record/<int:record_id>",
    methods=["PUT"]
)
@jwt_required()
@role_required("faculty", "admin")
def override_academic_record(
    student_id,
    record_id
):
    """Faculty/Admin manually updates academic record."""

    record = AcademicRecord.query.filter_by(
        id=record_id,
        user_id=student_id
    ).first_or_404()

    data = request.get_json(silent=True) or {}

    allowed_fields = [
        "attendance_percentage",
        "study_hours",
        "previous_exam_score",
        "assignment_marks",
        "internal_assessment_marks",
        "class_participation",
        "extracurricular_involvement"
    ]

    for field in allowed_fields:

        if field in data:
            setattr(
                record,
                field,
                data[field]
            )

    try:

        db.session.commit()

        return jsonify({
            "status": "success",
            "data": record.to_dict()
        }), 200

    except Exception as e:

        db.session.rollback()

        logger.error(
            f"Error updating academic record: {e}",
            exc_info=True
        )

        return jsonify({
            "status": "error",
            "error": "Unable to update academic record"
        }), 500


# ============================================================
# STUDENT DIRECTORY
# ============================================================

@cms_bp.route("/students", methods=["GET"])
@jwt_required()
@role_required("faculty", "admin")
def get_all_students():
    """Faculty/Admin views all students."""

    students = (
        User.query
        .filter_by(role="student")
        .all()
    )

    data = []

    for student in students:

        latest_record = (
            AcademicRecord.query
            .filter_by(user_id=student.id)
            .order_by(
                AcademicRecord.created_at.desc()
            )
            .first()
        )

        data.append({
            "id": student.id,
            "formatted_id": str(student.id).zfill(3),
            "name": student.name,
            "email": student.email,
            "latest_record": (
                latest_record.to_dict()
                if latest_record
                else None
            )
        })

    return jsonify({
        "status": "success",
        "data": data
    }), 200


# ============================================================
# CREATE / UPDATE STUDENT ACADEMIC RECORD
# ============================================================

@cms_bp.route(
    "/student/<int:student_id>/academic",
    methods=["POST"]
)
@jwt_required()
@role_required("faculty", "admin")
def update_student_academic(student_id):
    """
    Faculty/Admin creates a new academic record
    and generates prediction.
    """

    student = User.query.filter_by(
        id=student_id,
        role="student"
    ).first_or_404()

    data = request.get_json(silent=True) or {}

    try:

        record = AcademicRecord(
            user_id=student.id,

            attendance_percentage=float(
                data.get(
                    "attendance_percentage",
                    0
                )
            ),

            study_hours=float(
                data.get(
                    "study_hours",
                    0
                )
            ),

            previous_exam_score=float(
                data.get(
                    "previous_exam_score",
                    0
                )
            ),

            assignment_marks=float(
                data.get(
                    "assignment_marks",
                    0
                )
            ),

            internal_assessment_marks=float(
                data.get(
                    "internal_assessment_marks",
                    0
                )
            ),

            class_participation=float(
                data.get(
                    "class_participation",
                    0
                )
            ),


            extracurricular_involvement=data.get(
                "extracurricular_involvement",
                "none"
            )
        )

        db.session.add(record)
        db.session.flush()

        # Generate prediction
        score = calculate_dummy_score(record)
        category = get_performance_category(score)

        prediction = Prediction(
            user_id=student.id,
            record_id=record.id,
            predicted_score=score,
            category=category
        )

        db.session.add(prediction)
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": (
                "Academic record and prediction "
                "updated successfully"
            ),
            "data": record.to_dict(),
            "prediction": prediction.to_dict()
        }), 200

    except Exception as e:

        db.session.rollback()

        logger.error(
            f"Error updating academic record: {e}",
            exc_info=True
        )

        return jsonify({
            "status": "error",
            "error": "Unable to update academic record"
        }), 500
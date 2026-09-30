from collections import Counter

from app.models import SurveyAnswer


def survey_results(db, survey, include_text=False):
    # Older submissions may contain duplicates; count each person's latest answer.
    latest = {}
    anonymous = []
    for answer in db.query(SurveyAnswer).filter_by(survey_id=survey.id).order_by(SurveyAnswer.id):
        if answer.user_id is None:
            anonymous.append(answer)
        else:
            latest[(answer.user_id, answer.question_id)] = answer
    answers = list(latest.values()) + anonymous
    grouped = []
    for question in sorted(survey.questions, key=lambda q: q.id):
        values = [a.answer_text for a in answers if a.question_id == question.id]
        counts = None
        if question.question_type == "single_choice":
            counts = {key.strip(): 0 for key in (question.options_text or "").splitlines() if key.strip()}
            counts.update(Counter(values))
        grouped.append({"question": question, "counts": counts,
                        "answers": values if include_text else [], "total": len(values)})
    return {"grouped": grouped, "total_answers": len(answers),
            "respondents": len({a.user_id for a in answers if a.user_id is not None})}

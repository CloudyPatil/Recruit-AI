def calculate_round1_score(evaluations):
    if not evaluations:
        return 0
    
    total_score = 0
    zero_count = 0
    
    for e in evaluations:
        score = e.get("score", 0)
        total_score += score
        if score == 0:
            zero_count += 1
    
    avg = total_score / len(evaluations)
    base_score = (avg / 10) * 100
    
    # Extra penalty if many zeros (candidate didn't try)
    if zero_count >= len(evaluations) * 0.4:  # 40%+ zeros
        base_score *= 0.5
    
    return round(base_score, 2)


def calculate_round2_score(answers, questions):
    """
    Speed bonus scoring:
    - Correct = base 6
    - ≤15 sec = +4 bonus
    - ≤30 sec = +2 bonus
    - >30 sec = +0
    Max per Q = 10
    """
    total_score = 0
    
    for q in questions:
        q_id = str(q["question_id"])
        ans_data = answers.get(q_id, {})
        
        if isinstance(ans_data, dict):
            selected = ans_data.get("selected", "")
            time_taken = ans_data.get("time_taken", 60)
        else:
            selected = ans_data
            time_taken = 60
        
        if selected == q["correct_answer"]:
            base = 6
            if time_taken <= 15:
                bonus = 4
            elif time_taken <= 30:
                bonus = 2
            else:
                bonus = 0
            total_score += (base + bonus)
    
    total_possible = len(questions) * 10
    if total_possible == 0:
        return 0
    return round((total_score / total_possible) * 100, 2)


def calculate_round3_score(evaluation):
    keys = ["technical", "communication", "problem_solving"]
    scores = [evaluation.get(k, 0) for k in keys]
    avg = sum(scores) / len(scores)
    base_score = (avg / 10) * 100
    
    # If too many wrong answers, apply penalty
    correct = evaluation.get("correct_answers_count", 0)
    total = evaluation.get("total_questions", 1)
    
    if total > 0:
        accuracy = correct / total
        if accuracy < 0.3:  # Less than 30% correct
            base_score *= 0.4
        elif accuracy < 0.5:  # Less than 50% correct
            base_score *= 0.7
    
    return round(base_score, 2)


def calculate_final_score(ml, r1, r2, r3):
    final = (ml * 0.10) + (r1 * 0.20) + (r2 * 0.25) + (r3 * 0.45)
    return round(final, 2)
from datetime import date, timedelta

def sm2_update(repetitions, efactor, interval, quality):
    """
    Обновляет параметры интервального повторения (алгоритм SM-2).
    repetitions : сколько раз уже повторяли
    efactor     : фактор сложности (обычно 2.5)
    interval    : текущий интервал (в днях)
    quality     : оценка (0–5)
    """

    if quality < 3:
        repetitions = 0
        interval = 1
    else:
        if repetitions == 0:
            interval = 1
        elif repetitions == 1:
            interval = 6
        else:
            interval = round(interval * efactor)
        repetitions += 1

    efactor = efactor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    if efactor < 1.3:
        efactor = 1.3

    next_review_date = date.today() + timedelta(days=interval)
    return repetitions, efactor, interval, next_review_date

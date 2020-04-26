from datetime import datetime, timedelta

scores = [
    'complete blackout',
    'incorrect response; the correct one remembered',
    'incorrect response; where the correct one seemed easy to recall',
    'correct response recalled with serious difficulty',
    'correct response after a hesitation',
    'perfect response'
]


class Card(object):
    def __init__(self, idx, question, answer, first_practice, next_practice,
                 streak, interval, easiness):
        self.idx = idx
        self.question = question
        self.answer = answer
        self.first_practice = first_practice
        self.next_practice = next_practice
        self.streak = int(streak) if streak else 0
        self.interval = float(interval) if interval else 1
        self.easiness = float(easiness) if easiness else 2.5
        self.question_picture = None
        self.answer_picture = None

    def update(self, score):
        if score < 3:
            self.streak = 0
        else:
            self.streak += 1

        self.easiness = max(
            1.3,  self.easiness + 0.1 - (5.0 - score) * (0.08 + (5.0 - score) * 0.02))

        if self.streak == 0:
            self.interval = 0
        elif self.streak == 1:
            self.interval = 1
        elif self.streak == 2:
            self.interval = 4
        else:
            self.interval = self.interval * self.easiness

        if not self.first_practice:
            self.first_practice = datetime.now().isoformat()

        self.next_practice = (
            datetime.now() + timedelta(days=self.interval)).isoformat()

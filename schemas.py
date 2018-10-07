"""
API contract
"""
from tricks import marshmallow


class CheckInSchema(marshmallow.Schema):
    class Meta:
        fields = ('id', 'group', 'room', 'checkin_dt')


class ConfigSchema(marshmallow.Schema):
    class Meta:
        fields = ('id', 'config_name', 'challenge_limit')


class RoomSchema(marshmallow.Schema):
    class Meta:
        fields = ('id', 'room_name')


class GroupSchema(marshmallow.Schema):
    class Meta:
        fields = ('id', 'group_name')


class QuestionsAnswersSchema(marshmallow.Schema):
    class Meta:
        fields = ('id', 'question_number', 'question_text', 'num_points')


class GroupAnswersSchema(marshmallow.Schema):
    class Meta:
        fields = ('id', 'answer', 'question', 'room', 'group')

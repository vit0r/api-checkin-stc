import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String, Float, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from tricks import db


class Configuration(db.Model):
    __tablename__ = 'config'

    id = db.Column(UUID(as_uuid=True), primary_key=True, unique=True, default=uuid.uuid4)
    config_name = Column(String(50), nullable=False, unique=True)
    challenge_limit = Column(Float, nullable=False, unique=True)
    create_at = Column(DateTime, default=datetime.utcnow())

    def __repr__(self):
        return '{}.{}'.format(self.__class__.__name__, self.id)


class Room(db.Model):
    __tablename__ = 'room'

    id = db.Column(UUID(as_uuid=True), primary_key=True, unique=True, default=uuid.uuid4)
    room_name = Column(String(50), nullable=False, unique=True)
    create_at = Column(DateTime, default=datetime.utcnow())

    def __repr__(self):
        return '{}.{}'.format(self.__class__.__name__, self.id)


class Group(db.Model):
    __tablename__ = 'group'

    id = db.Column(UUID(as_uuid=True), primary_key=True, unique=True, default=uuid.uuid4)
    group_name = Column(String(50), nullable=False, unique=True)
    create_at = Column(DateTime, default=datetime.utcnow())

    def __repr__(self):
        return '{}.{}'.format(self.__class__.__name__, self.id)


class CheckIn(db.Model):
    __tablename__ = 'checkin'

    id = db.Column(UUID(as_uuid=True), primary_key=True, unique=True, default=uuid.uuid4)
    group = Column(UUID, ForeignKey('group.id'))
    id_group = relationship(Group, lazy='joined')
    room = Column(UUID, ForeignKey('room.id'))
    id_room = relationship(Room, lazy='joined')
    checkin_dt = Column(DateTime, default=datetime.utcnow())
    __table_args__ = (db.UniqueConstraint('group', 'room'),)

    def __repr__(self):
        return '{}.{}'.format(self.__class__.__name__, self.id)


class QuestionsAnswers(db.Model):
    __tablename__ = 'questions_answers'

    id = db.Column(UUID(as_uuid=True), primary_key=True, unique=True, default=uuid.uuid4)
    question_number = Column(Integer, nullable=False)
    question_text = Column(String(200), nullable=False)
    answer = Column(String(500), nullable=False)
    num_points = Column(Float, nullable=False)
    room = Column(UUID, ForeignKey('room.id'))
    id_room = relationship(Room, lazy='joined')
    create_at = Column(DateTime, default=datetime.utcnow())
    __table_args__ = (db.UniqueConstraint('question_number', 'room'),)

    def __repr__(self):
        return '{}.{}'.format(self.__class__.__name__, self.id)


class GroupAnswers(db.Model):
    __tablename__ = 'group_answers'

    id = db.Column(UUID(as_uuid=True), primary_key=True, unique=True, default=uuid.uuid4)
    answer = Column(String(500), nullable=False)
    question = Column(UUID, ForeignKey('questions_answers.id'))
    room = Column(UUID, ForeignKey('room.id'))
    group = Column(UUID, ForeignKey('group.id'))
    id_room = relationship(Room, lazy='joined')
    id_question = relationship(QuestionsAnswers, lazy='joined')
    id_group = relationship(Group, lazy='joined')
    create_at = Column(DateTime, default=datetime.utcnow())

    def __repr__(self):
        return '{}.{}'.format(self.__class__.__name__, self.id)

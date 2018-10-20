import json
import os
from datetime import datetime, timedelta

import pytz
from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin

from models import CheckIn, Configuration, Room, Group, QuestionsAnswers, GroupAnswers
from schemas import RoomSchema, GroupSchema, QuestionsAnswersSchema, CheckInSchema, GroupAnswersSchema, ConfigSchema
from tricks import db, migrate, marshmallow, db_session


def create_app():
    app = Flask(__name__)
    CORS(app, resources={r'/api/*': {'origins': '*'}})
    app.config['SECRET_KEY'] = os.urandom(32)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    SQL_TESTDB_URI = 'postgres://postgres:postgres@localhost:5432/checkindb'
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', SQL_TESTDB_URI)
    app.config['JSON_SORT_KEYS'] = False
    app.url_map.strict_slashes = False

    db.init_app(app)
    migrate.init_app(app, db)
    marshmallow.init_app(app)

    def get_question_answer(question_number, room_id):
        question_answer = QuestionsAnswers.query.filter(QuestionsAnswers.question_number == question_number,
                                                        QuestionsAnswers.room == room_id).first()
        return question_answer

    def get_group_answers(group_id, room_id, question_id, ok_answer):
        wrong_answers = GroupAnswers.query.filter(GroupAnswers.group == group_id,
                                                  GroupAnswers.question == question_id,
                                                  GroupAnswers.room == room_id,
                                                  GroupAnswers.answer != ok_answer).all()
        correct_answers = GroupAnswers.query.filter(GroupAnswers.group == group_id,
                                                    GroupAnswers.question == question_id,
                                                    GroupAnswers.room == room_id,
                                                    GroupAnswers.answer == ok_answer).all()

        return wrong_answers, correct_answers

    def group_checkin(room_id, group_id):
        checkin_model = CheckIn.query.filter(CheckIn.group == group_id, CheckIn.room == room_id).first()
        return checkin_model

    def group_check_limit_time(checkin_data):
        tz = pytz.timezone('America/Sao_Paulo')
        config_model = Configuration.query.filter(Configuration.config_name == 'settimelimit').first()
        limit_datetime = checkin_data.checkin_dt + timedelta(hours=config_model.challenge_limit)
        current_datetime = datetime.utcnow().replace(tzinfo=pytz.UTC)
        curtime_tz = current_datetime.astimezone(tz).timestamp()
        lmttime_tz = limit_datetime.astimezone(tz).timestamp()
        return curtime_tz <= lmttime_tz

    def check_num_attempts(room_id, group_id, question_answer_ok, num_attempts_limit=10):
        config_model = Configuration.query.filter(Configuration.config_name == 'limitanswersatt').first()
        if not config_model:
            num_attempts_limit = config_model.challenge_limit
        num_wrong_attempts = GroupAnswers.query.filter(GroupAnswers.room == room_id, GroupAnswers.group == group_id,
                                                       GroupAnswers.answer != question_answer_ok).count()
        return num_wrong_attempts < num_attempts_limit

    def check_group_valid_answer(room_id, question_answer_id, question_answer_ok, group_id, answer_text):
        hasvalid_answer = question_answer_ok == answer_text
        wrong_answers, correct_answers = get_group_answers(group_id, room_id, question_answer_id, question_answer_ok)
        return hasvalid_answer, wrong_answers, correct_answers

    def create_response(status_code, data):
        response = jsonify(data)
        response.status_code = status_code
        return response

    @app.errorhandler(404)
    @cross_origin()
    def not_found(error=None):
        data = {
            'status': 404,
            'message': 'Not Found: {}'.format(request.url, error),
        }
        create_response(404, data)

    @app.errorhandler(500)
    @cross_origin()
    def internal_error(error=None):
        data = {
            'status': 500,
            'message': 'Internal error : {}'.format(request.url, error),
        }
        create_response(500, data)

    @app.route('/')
    @cross_origin()
    def index():
        return create_response(200, {'ok': True})

    @app.route('/api/group/checkin/', methods=['POST'])
    @cross_origin()
    def checkin():
        '''
        :input: {'group':'cbb9cf31-cee5-4208-bfea-654646c83f6d','room':'bdac321b-c65d-463a-97e1-05a11f98024a'}
        :return: boolean
        '''
        json_body = request.get_json()
        issuccess = db_session(CheckIn, json_body, request.method)
        return create_response(201, {'status': issuccess})

    @app.route('/api/group/checkin/<group_id>/<room_id>', methods=['GET'])
    @cross_origin()
    def checkin_group(group_id, room_id):
        checkin_model = group_checkin(room_id, group_id)
        if not checkin_model:
            return create_response(204, {'message_code': 'GNC204'})
        return CheckInSchema().jsonify(checkin_model)

    @app.route('/api/config/', defaults={'config_id': None}, methods=['POST'])
    @app.route('/api/config/<config_id>/', methods=['PATCH', 'PUT'])
    @cross_origin()
    def config(config_id):
        '''
        :input: {'config_name':'settimelimit','challenge_limit':2}
        :return: {'config_name':'settimelimit','challenge_limit':2 in hours}
        '''
        json_body = request.get_json()
        issuccess = db_session(Configuration, json_body, id=config_id)
        return create_response(201, {'status': issuccess})

    @app.route('/api/config/<config_id>', methods=['GET'])
    @app.route('/api/configs/', defaults={'config_id': None}, methods=['GET'])
    @cross_origin()
    def configs(config_id):
        '''
        :return: {'config_name':'settimelimit','challenge_limit':2}
        '''
        if config_id:
            config_model = Configuration.query.get(config_id)
            return ConfigSchema().jsonify(config_model)
        config_model = Configuration.query.all()
        return ConfigSchema().jsonify(config_model, many=True)

    @app.route('/api/group/<group_id>', methods=['GET'])
    @app.route('/api/groups/', defaults={'group_id': None}, methods=['GET'])
    @cross_origin()
    def groups(group_id):
        if isinstance(group_id, str):
            group_model = Group.query.get(group_id)
            return GroupSchema().jsonify(group_model)
        groups_model = Group.query.all()
        return GroupSchema().jsonify(groups_model, many=True)

    @app.route('/api/group/', defaults={'group_id': None}, methods=['POST'])
    @app.route('/api/group/<group_id>/', methods=['PUT', 'PATCH'])
    @cross_origin()
    def group(group_id):
        '''
        :input: {'group_name':'feliz'}
        :return: boolean
        '''
        json_body = request.get_json()
        issuccess = db_session(Group, json_body, request.method, id=group_id)
        return create_response(201, {'status': issuccess})

    @app.route('/api/room/<room_id>/', methods=['PUT', 'PATCH'])
    @app.route('/api/room/', methods=['POST'], defaults={'room_id': None})
    @cross_origin()
    def room(room_id):
        '''
        :input: {'room_name':'nodejs'}
        :return: boolean
        '''
        json_body = request.get_json()
        issuccess = db_session(Room, json_body, request.method, id=room_id)
        return create_response(201, {'status': issuccess})

    @app.route('/api/room/<room_id>', methods=['GET'])
    @app.route('/api/rooms/', defaults={'room_id': None}, methods=['GET'])
    @cross_origin()
    def rooms(room_id):
        if isinstance(room_id, str):
            room_model = Room.query.get(room_id)
            return RoomSchema().jsonify(room_model)
        room_model = Room.query.all()
        return RoomSchema().jsonify(room_model, many=True)

    @app.route('/api/room/qa/<room_id>/<int:qa_id>/', methods=['PUT', 'PATCH'])
    @app.route('/api/room/qa/', defaults={'room_id': None, 'qa_id': None}, methods=['POST'])
    @cross_origin()
    def room_questions_answers(room_id, qa_id):
        '''
        :input: {
            'question': 5,
            'answer':'sua resposta5',
            'num_points':5,
            'room':'9efcb329-4242-42ba-a1bf-2305f80c86cd'
        } or list
        :return: boolean
        '''
        json_body = request.get_json()
        issuccess = db_session(QuestionsAnswers, json_body, request.method, id=qa_id, room_id=room_id)
        return create_response(201, {'status': issuccess})

    @app.route('/api/room/qa/<room_id>/<int:qa_id>/', methods=['GET'])
    @app.route('/api/room/qa/<room_id>/', defaults={'qa_id': None}, methods=['GET'])
    @cross_origin()
    def room_qa(room_id, qa_id):
        hasqa_id = isinstance(qa_id, int)
        if hasqa_id:
            room_qa_model = QuestionsAnswers.query.filter(QuestionsAnswers.room == room_id,
                                                          QuestionsAnswers.id == qa_id).first()
        else:
            room_qa_model = QuestionsAnswers.query.filter(QuestionsAnswers.room == room_id)
        return QuestionsAnswersSchema().jsonify(room_qa_model, many=(not hasqa_id))

    @app.route('/api/group/answer/', methods=['POST'])
    @cross_origin()
    def group_answer():
        '''
        :input: {
            'question': 5,
            'answer':'sua resposta5',
            'room':'9efcb329-4242-42ba-a1bf-2305f80c86cd',
            'group':'9efcb329-4242-42ba-a1bf-2305f80c86cd'
        }
        :return: try number
        '''
        json_body = request.get_json()
        room_id = json_body.get('room')
        group_id = json_body.get('group')
        question_id = json_body.get('question')
        answer_text = json_body.get('answer')
        checkin_data = group_checkin(room_id, group_id)
        if not checkin_data:
            return create_response(203, {'message_code': 'GNC203'})
        if not group_check_limit_time(checkin_data):
            return create_response(503, {'message_code': 'GTT503'})
        question_answer = get_question_answer(question_id, room_id)
        if not question_answer:
            return create_response(500, {'message_code': 'QNF500'})
        question_answer_id = str(question_answer.id)
        question_answer_ok = question_answer.answer
        json_body.update({'question': question_answer_id})
        wrong_answers, correct_answers = get_group_answers(group_id, room_id, question_answer_id, question_answer_ok)
        if not correct_answers:
            if not check_num_attempts(room_id, group_id, question_answer_ok):
                return create_response(503, {'message_code': 'GTO503'})
            inserted = db_session(GroupAnswers, json_body, request.method, group_id=group_id, room_id=room_id)
            if not inserted:
                return create_response(500, {'message_code': 'NIE500'})
            has_valid_answer, wrong_answers, correct_answers = check_group_valid_answer(room_id, question_answer_id,
                                                                                        question_answer_ok,
                                                                                        group_id, answer_text)
            if has_valid_answer:
                return create_response(201, {'message_code': 'GTS201'})
            return GroupAnswersSchema().jsonify(wrong_answers, many=True)
        return create_response(302, {'message_code': 'GAO302'})

    @app.route('/api/challenge/1/answer/', methods=['GET'])
    @cross_origin()
    def challenge_one_answer():
        response_one = str(os.environ.get('RESPONSE_CODES_ONE', '')).upper()
        if not response_one:
            return create_response(500, {'message': 'response not found'})
        codes = str(request.values.get('codes', '')).upper()
        if not codes:
            return create_response(403, {'message': 'Informe sua resposta ex: codes=codigo1,codigo2'})
        if response_one == codes:
            code_ok = int(os.environ.get('CODE_OK', 0))
            return create_response(200, {'message': 'Resposta correta', 'codigo': code_ok})
        return create_response(403, {'message': 'Resposta incorreta'})

    @app.route('/api/tools/', methods=['GET'])
    @cross_origin()
    def tools():
        tool_list = [
            {'id': 5, 'name': 'ALAVANCA 1', 'country': 'Brazil', 'code': ''},
            {'id': 8, 'name': 'PICARETA ESTREITA', 'country': 'Norway', 'code': ''},
            {'id': 3, 'name': 'CAVADEIRA RETA', 'country': 'Germany', 'code': ''},
            {'id': 6, 'name': 'LANTERNA', 'country': 'USA', 'code': ''},
            {'id': 1, 'name': 'PICARETA CHIBANCA', 'country': 'Japan', 'code': ''},
            {'id': 7, 'name': 'ENXADA DUAS CARAS LARGA', 'country': 'Finland', 'code': ''},
            {'id': 4, 'name': 'TRADO SATO', 'country': 'Kenya', 'code': ''},
            {'id': 2, 'name': 'SACHO DUAS PONTAS', 'country': 'Russia', 'code': ''}
        ]
        return create_response(200, tool_list)

    @app.route('/api/challenge/6/', methods=['GET'])
    @cross_origin()
    def challenge_six_message():
        six_possible = str(os.environ.get('POSSIBLE', ''))
        six_message = str(os.environ.get('MESSAGE_SIX', ''))
        return create_response(200, {'possible': six_possible, 'message': six_message})

    @app.route('/api/challenge/6/answer/', methods=['GET'])
    @cross_origin()
    def challenge_six_answer():
        phone = str(request.values.get('phone', '')).upper()
        if not phone:
            return create_response(403, {'message': 'Informe sua resposta ex: ?phone=phone_found'})
        phone_ok = str(os.environ.get('PHONE_OK', ''))
        if phone_ok == phone:
            return create_response(200, {'message': 'Resposta correta', 'phone': phone_ok})
        return create_response(403, {'message': 'Resposta incorreta'})

    print(app.url_map)
    return app

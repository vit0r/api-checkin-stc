from flask_marshmallow import Marshmallow
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError

db = SQLAlchemy()
migrate = Migrate()
marshmallow = Marshmallow()


def db_session(model, input_json, method='POST', **kwargs):
    has_noerror = True
    if isinstance(input_json, list):
        for d in input_json:
            data_model = model(**d)
            __create_or_update(model, data_model, method, **kwargs)
    else:
        data_model = model(**input_json)
        __create_or_update(model, data_model, method, **kwargs)
    try:
        db.session.commit()
    except SQLAlchemyError as sae:
        print(sae)
        has_noerror = False
    finally:
        db.session.close()
    return has_noerror


def __create_or_update(model, data_model, method, **kwargs):
    id = kwargs.get('id')
    hasid = isinstance(id, int) or isinstance(id, str)
    if method == 'POST' and not hasid:
        db.session.add(data_model)
    elif method in ['PUT', 'PATCH'] and hasid:
        old_data = model.query.get(id)
        if kwargs.get('room_id'):
            assert old_data.room == kwargs.get('room_id')
            data_model.room = old_data.room
        if kwargs.get('group_id'):
            assert old_data.group == kwargs.get('group_id')
            data_model.group = old_data.group
        data_model.id = old_data.id
        db.session.merge(data_model)

from datetime import date
from typing import Literal

from fastapi import Depends, FastAPI, Header, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StrictBool

from .regions import REGIONS
from .store import Problem, Store


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Enroll(Input):
    invite_code: str = Field(min_length=1, max_length=128)


class CheckIn(Input):
    region_code: str = Field(pattern=r'^[0-9]{6}$')
    symptom: Literal['new', 'ongoing', 'none']
    observation: Literal['more', 'usual', 'less'] | None = None
    consent: StrictBool


def bearer(authorization: str = Header(default='')):
    scheme, _, value = authorization.partition(' ')
    if scheme.lower() != 'bearer' or not 1 <= len(value) <= 128:
        raise Problem(401, 'Bearer credential required')
    return value


def parse_day(day):
    try:
        value = date.fromisoformat(day)
        if value.isoformat() != day:
            raise ValueError()
        return value
    except ValueError:
        raise Problem(422, 'Expected YYYY-MM-DD') from None


def create_app(store=None):
    store = store or Store.configured()
    app = FastAPI(title='Community weekly pilot', docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware('http')
    async def headers(request, call_next):
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Referrer-Policy'] = 'no-referrer'
        if request.method == 'GET' and request.url.path in ('/v1/regions', '/v1/reports/latest'):
            response.headers['Access-Control-Allow-Origin'] = '*'
        return response

    @app.exception_handler(Problem)
    async def problem(request, exc):
        return JSONResponse(status_code=exc.status, content={'detail': str(exc)})

    @app.exception_handler(RequestValidationError)
    async def invalid(request, exc):
        # Never echo credentials, health data, or unexpected fields in errors.
        return JSONResponse(status_code=422, content={'detail': 'Invalid request'})

    @app.post('/v1/enroll')
    def enroll(body: Enroll):
        return {'token': store.enroll(body.invite_code)}

    @app.get('/v1/checkins/{day}')
    def get(day: str, token=Depends(bearer)):
        return store.entry('get', token, parse_day(day))

    @app.put('/v1/checkins/{day}')
    def put(day: str, body: CheckIn, token=Depends(bearer)):
        return store.entry('put', token, parse_day(day), body.region_code, body.symptom, body.observation, body.consent)

    @app.delete('/v1/checkins/{day}', status_code=204)
    def delete(day: str, token=Depends(bearer)):
        store.entry('delete', token, parse_day(day))
        return Response(status_code=204)

    @app.get('/v1/regions')
    def regions():
        return {'regions': list(REGIONS.values())}

    @app.get('/v1/reports/latest')
    def latest(region_code: str = '000000'):
        return store.latest(region_code)

    return app

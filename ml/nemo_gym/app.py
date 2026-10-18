"""Official NeMo Gym v0.6.0 resource-server adapter; no fallback imitation."""
import json
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from nemo_gym.base_resources_server import (
    BaseResourcesServerConfig, BaseRunRequest, BaseVerifyRequest,
    BaseVerifyResponse, BaseSeedSessionRequest, BaseSeedSessionResponse,
    SimpleResourcesServer, ReverifyMode,
)
from nemo_gym.server_utils import ServerClient
from nemo_gym.config_types import BaseServerConfig
from omegaconf import OmegaConf
from pydantic import PrivateAttr
from ml.nemo_gym.core import Scenario, EmptyRequest, GraphRequest, Recommendation, tool_result, score

class RescueConfig(BaseResourcesServerConfig):
    data_dir: str = str(Path(__file__).parent/'data')
    REVERIFY_MODE = ReverifyMode.STATELESS

class RescueRunRequest(BaseRunRequest):
    scenario_id: str

class RescueVerifyRequest(RescueRunRequest, BaseVerifyRequest):
    pass

class RescueVerifyResponse(BaseVerifyResponse):
    scenario_id: str
    expected_status: str
    issues: list[str]
    correct_reachability: bool
    valid_candidate_path: bool
    required_tools_called: bool

class SeedRequest(BaseSeedSessionRequest):
    scenario_id: str

class SeedResponse(BaseSeedSessionResponse):
    initialized: bool

class RescueResourcesServer(SimpleResourcesServer):
    config: RescueConfig
    _scenarios: dict[str,Scenario] = PrivateAttr(default_factory=dict)

    def scenario(self,scenario_id):
        if not self._scenarios:
            for path in sorted(Path(self.config.data_dir).glob('*.jsonl')):
                for line in path.read_text().splitlines():
                    row=json.loads(line); parsed=Scenario.model_validate(row['scenario'])
                    if parsed.scenario_id in self._scenarios:raise ValueError('Duplicate scenario ID')
                    self._scenarios[parsed.scenario_id]=parsed
        if scenario_id not in self._scenarios:raise HTTPException(404,'Unknown scenario_id')
        return self._scenarios[scenario_id]

    def session_scenario(self,request):
        scenario_id=request.session.get('sosora_scenario_id')
        if not scenario_id:raise HTTPException(409,'Call seed_session for this rollout first')
        return self.scenario(scenario_id)

    async def seed_session(self,body:SeedRequest,request:Request)->SeedResponse:
        self.scenario(body.scenario_id)
        request.session['sosora_scenario_id']=body.scenario_id
        return SeedResponse(initialized=True)

    def setup_webserver(self)->FastAPI:
        app=super().setup_webserver()
        app.post('/get_incident')(self.get_incident)
        app.post('/get_road_status')(self.get_road_status)
        app.post('/calculate_candidate_routes')(self.calculate_candidate_routes)
        app.post('/check_reachability')(self.check_reachability)
        app.post('/get_damage_evidence')(self.get_damage_evidence)
        app.post('/submit_recommendation')(self.submit_recommendation)
        return app

    async def get_incident(self,body:EmptyRequest,request:Request)->dict:
        return tool_result(self.session_scenario(request),'get_incident',body.model_dump())
    async def get_road_status(self,body:EmptyRequest,request:Request)->dict:
        return tool_result(self.session_scenario(request),'get_road_status',body.model_dump())
    async def calculate_candidate_routes(self,body:GraphRequest,request:Request)->dict:
        return tool_result(self.session_scenario(request),'calculate_candidate_routes',body.model_dump())
    async def check_reachability(self,body:GraphRequest,request:Request)->dict:
        return tool_result(self.session_scenario(request),'check_reachability',body.model_dump())
    async def get_damage_evidence(self,body:EmptyRequest,request:Request)->dict:
        return tool_result(self.session_scenario(request),'get_damage_evidence',body.model_dump())
    async def submit_recommendation(self,body:Recommendation,request:Request)->dict:
        return tool_result(self.session_scenario(request),'submit_recommendation',body.model_dump())

    async def verify(self,body:RescueVerifyRequest)->RescueVerifyResponse:
        calls=[]
        for item in body.response.output:
            if item.type=='function_call':
                name=self.normalize_tool_name(item.name)
                try:args=json.loads(item.arguments)
                except (ValueError,TypeError):args=None
                calls.append((name,args))
        result=score(self.scenario(body.scenario_id),calls)
        return RescueVerifyResponse(**body.model_dump(),**result)


def local_app(data_dir=None):
    """Run the real Gym server class standalone for local integration tests.
    No head service/model calls or Ray cluster needed for these tool endpoints.
    """
    config=RescueConfig(host='127.0.0.1',port=8012,name='sosora_resources_server',entrypoint='app.py',**({'data_dir':str(data_dir)} if data_dir else {}))
    client=ServerClient(head_server_config=BaseServerConfig(host='127.0.0.1',port=11000),global_config_dict=OmegaConf.create({}))
    return RescueResourcesServer(config=config,server_client=client).setup_webserver()

if __name__=='__main__':
    RescueResourcesServer.run_webserver()

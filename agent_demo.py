import json
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

# ==========================================
# 1. 실행 가능한 API/함수 계층 (The "Hands")
# ==========================================

# 실제 프로젝트의 Service를 모방한 Mock Service입니다.
# 실제 환경에서는 src/application/sync_service.py를 import해서 사용합니다.
@dataclass
class SyncStatus:
    state: str
    result: Optional[dict] = None

class MockSyncService:
    def __init__(self):
        self.status = SyncStatus(state='idle')

    def get_status(self) -> dict:
        """현재 동기화 상태를 반환합니다."""
        return {"state": self.status.state, "last_result": self.status.result}

    def start_sync(self, table_name: str) -> dict:
        """
        특정 테이블의 동기화 작업을 시작합니다.
        """
        print(f"\n[System] '{table_name}' 테이블 동기화 프로세스 시작 중...")
        self.status.state = 'running'
        
        # 실제 작업 시뮬레이션 (시간 소요)
        time.sleep(1) 
        
        # 결과 모의 생성
        result = {
            "table": table_name,
            "processed_rows": 150,
            "status": "success",
            "timestamp": "2026-01-12 10:00:00"
        }
        self.status = SyncStatus(state='completed', result=result)
        
        print(f"[System] 동기화 완료: 150건 처리됨.")
        return result

# ==========================================
# 2. 함수 정의 스키마 (The "Manual")
# ==========================================

# LLM에게 제공할 도구(Tool) 정의입니다.
# OpenAI Function Calling 포맷을 따릅니다.
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "start_sync",
            "description": "Oracle 데이터베이스에서 지정된 테이블의 데이터를 동기화합니다. 사용자가 동기화를 요청할 때 사용합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "동기화할 Oracle 테이블의 이름 (예: USERS, ORDERS)"
                    }
                },
                "required": ["table_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_status",
            "description": "현재 동기화 시스템의 상태나 진행 상황을 확인합니다.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

# ==========================================
# 3. AI Agent 오케스트레이터 (The "Brain")
# ==========================================

class ERPAgent:
    def __init__(self, service: MockSyncService):
        self.service = service
        # 실제 환경에서는 여기에 OpenAI Client 등이 들어갑니다.
    
    def process_query(self, user_query: str):
        print(f"\nUSER: {user_query}")
        
        # 1. Intent Recognition (LLM 시뮬레이션)
        # 실제로는 LLM API에 (user_query + TOOLS_SCHEMA)를 보냅니다.
        # 여기서는 데모를 위해 간단한 키워드 매칭으로 LLM의 판단을 흉내냅니다.
        
        llm_decision = self._simulate_llm_reasoning(user_query)
        
        if not llm_decision:
            print("AGENT: 죄송합니다. 요청하신 내용을 이해할 수 없거나 실행할 수 있는 도구가 없습니다.")
            return

        function_name = llm_decision["name"]
        arguments = llm_decision["arguments"]

        print(f"AGENT (Thought): 사용자가 '{function_name}' 도구를 실행하길 원합니다. 파라미터: {arguments}")

        # 2. Function Execution
        result = self._execute_tool(function_name, arguments)

        # 3. Final Response Generation
        # 도구 실행 결과를 바탕으로 최종 답변 생성
        final_response = self._generate_final_response(function_name, result)
        print(f"AGENT: {final_response}")

    def _simulate_llm_reasoning(self, query: str) -> Optional[dict]:
        """
        LLM이 질문을 분석하고 도구를 선택하는 과정을 시뮬레이션합니다.
        """
        if "동기화" in query or "sync" in query.lower():
            # Entity Extraction: 테이블 이름 추출 (단순화)
            table_name = "UNKNOWN"
            words = query.split()
            for word in words:
                if word not in ["동기화", "해줘", "테이블", "sync"]:
                    table_name = word.upper()  # 대문자로 변환
            
            return {
                "name": "start_sync",
                "arguments": {"table_name": table_name}
            }
            
        elif "상태" in query or "status" in query.lower():
            return {
                "name": "get_status",
                "arguments": {}
            }
            
        return None

    def _execute_tool(self, name: str, args: dict) -> dict:
        """선택된 도구를 실제로 실행합니다."""
        if name == "start_sync":
            return self.service.start_sync(args.get("table_name", "UNKNOWN"))
        elif name == "get_status":
            return self.service.get_status()
        return {"error": "Unknown tool"}

    def _generate_final_response(self, tool_name: str, tool_result: dict) -> str:
        """도구 실행 결과를 자연어로 변환합니다."""
        if tool_name == "start_sync":
            return f"요청하신 '{tool_result['table']}' 테이블의 동기화가 완료되었습니다. 총 {tool_result['processed_rows']}건의 데이터가 처리되었습니다."
        elif tool_name == "get_status":
            state = tool_result.get('state')
            if state == 'idle':
                return "현재 대기 중이며 실행 중인 작업은 없습니다."
            elif state == 'completed':
                return "최근 작업이 완료된 상태입니다."
            else:
                return f"현재 상태는 '{state}' 입니다."
        return "작업이 완료되었습니다."

# ==========================================
# 실행 (Main)
# ==========================================

if __name__ == "__main__":
    # 1. 서비스 초기화
    sync_service = MockSyncService()
    
    # 2. 에이전트 초기화
    agent = ERPAgent(sync_service)
    
    print("=== ERP AI Agent Prototype Started ===")
    print("사용 가능한 도구: start_sync, get_status")
    
    # 시나리오 1: 상태 확인
    agent.process_query("지금 시스템 상태 알려줘")
    
    # 시나리오 2: 동기화 요청
    agent.process_query("USERS 테이블 동기화 해줘")

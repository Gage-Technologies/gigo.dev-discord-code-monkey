
from enum import Enum
from typing import Optional
import requests
import json
from pydantic import BaseModel, Field

class ProgrammingLanguage(Enum):
    Java = "java"
    JavaScript = "javascript"
    TypeScript = "typescript"
    Python = "python"
    Go = "go"
    Cpp = "cpp"
    C = "c"
    Csharp = "csharp"
    Rust = "rust"

    def to_int(self) -> int:
        if self == ProgrammingLanguage.Java:
            return 2
        elif self == ProgrammingLanguage.JavaScript:
            return 3
        elif self == ProgrammingLanguage.TypeScript:
            return 4
        elif self == ProgrammingLanguage.Python:
            return 5
        elif self == ProgrammingLanguage.Go:
            return 6
        elif self == ProgrammingLanguage.Cpp:
            return 8
        elif self == ProgrammingLanguage.C:
            return 9
        elif self == ProgrammingLanguage.Csharp:
            return 10
        elif self == ProgrammingLanguage.Rust:
            return 14
        else:
            raise ValueError("Invalid ProgrammingLanguage")

    @staticmethod
    def from_int(x: int) -> 'ProgrammingLanguage':
        mapping = {
            2: ProgrammingLanguage.Java,
            3: ProgrammingLanguage.JavaScript,
            4: ProgrammingLanguage.TypeScript,
            5: ProgrammingLanguage.Python,
            6: ProgrammingLanguage.Go,
            8: ProgrammingLanguage.Cpp,
            9: ProgrammingLanguage.C,
            10: ProgrammingLanguage.Csharp,
            14: ProgrammingLanguage.Rust,
        }
        if x in mapping:
            return mapping[x]
        else:
            raise ValueError("Invalid integer for ProgrammingLanguage")

    @staticmethod
    def from_str(x: str) -> 'ProgrammingLanguage':
        mapping = {
            "python": ProgrammingLanguage.Python,
            "py": ProgrammingLanguage.Python,
            "go": ProgrammingLanguage.Go,
            "golang": ProgrammingLanguage.Go,
            "cpp": ProgrammingLanguage.Cpp,
            "c++": ProgrammingLanguage.Cpp,
            "cc": ProgrammingLanguage.Cpp,
            "cxx": ProgrammingLanguage.Cpp,
            "rust": ProgrammingLanguage.Rust,
            "rs": ProgrammingLanguage.Rust,
            "javascript": ProgrammingLanguage.JavaScript,
            "js": ProgrammingLanguage.JavaScript,
            "csharp": ProgrammingLanguage.Csharp,
            "cs": ProgrammingLanguage.Csharp,
            "c#": ProgrammingLanguage.Csharp,
            "java": ProgrammingLanguage.Java,
            "c": ProgrammingLanguage.C,
        }
        if x.lower() in mapping:
            return mapping[x.lower()]
        else:
            raise ValueError("Invalid string for ProgrammingLanguage")

class ChallengeType(Enum):
    Interactive = "interactive"
    Playground = "playground"
    Casual = "casual"
    Competitive = "competitive"

    @staticmethod
    def from_string_with_default(challenge_type_name: str) -> "ChallengeType":
        opts = {
            "interactive": ChallengeType.Interactive,
            "playground": ChallengeType.Playground,
            "casual": ChallengeType.Casual,
            "competitive": ChallengeType.Competitive,
        }
        try:
            return opts[challenge_type_name]
        except KeyError:
            return ChallengeType.Interactive

    @staticmethod
    def from_str(x: str) -> 'ChallengeType':
        mapping = {
            "playground": ChallengeType.Playground,
            "casual": ChallengeType.Casual,
            "competitive": ChallengeType.Competitive,
            "interactive": ChallengeType.Interactive
        }
        if x.lower() in mapping:
            return mapping[x.lower()]
        else:
            raise ValueError("Invalid string for ChallengeType")
        
    def to_int(self) -> int:
        return {
            "playground": 1,
            "casual": 2,
            "competitive": 3,
            "interactive": 0,
        }[self.value]


class ChallengeSearchParams(BaseModel):
    query: str = Field(..., description="Query that will be used to search for challenges. The query is searched both by keyword and semantic search.")
    language: Optional[ProgrammingLanguage] = Field(None, description="Filter results by programming language")
    renown: Optional[int] = Field(None, description="Filter results by renown (difficulty)", ge=0, le=9)
    challenge_type: Optional[ChallengeType] = Field(None, description="Filter results by challenge type")


def search_challenges(params: ChallengeSearchParams) -> str:
    p = {"query": params.query, "skip": 0, "limit": 10}
    if params.language:
        p["languages"] = [params.language.to_int()]
    if params.renown:
        p["tier"] = params.renown
    if params.challenge_type:
        p["challenge_type"] = params.challenge_type.to_int()

    res = requests.post(
        "https://api.cdn.gigo.dev/api/search/posts", 
        json=p
    )
    if res.status_code != 200:
        return f"<api_error>\nFailed to retrieve challenges from GIGO API:\n({res.status_code}) {res.text}\n</api_error>"
    

    data = [
        {
            "url": f"https://www.gigo.dev/challenge/{x['_id']}",
            "image": f"https://api.cdn.gigo.dev/static/posts/t/{x['_id']}",
            "name": x['title'],
            "description": x['description'],
            "renown": x['tier'],
            "languages": x['languages_strings'],
            "challenge_type": x['post_type_string']
        } for x in res.json()['challenges']
    ]
    return f"<api_response>\n{json.dumps(data)}\n</api_response>"


class ByteSearchParams(BaseModel):
    query: str = Field(..., description="Query that will be used to search for bytes. The query is searched both by keyword and semantic search.")
    language: Optional[ProgrammingLanguage] = Field(None, description="Filter results by programming language")


def search_bytes(params: ByteSearchParams) -> str:
    p = {"query": params.query, "skip": 0, "limit": 10}
    if params.language:
        p["languages"] = [params.language.to_int()]
    
    res = requests.post(
        "https://api.cdn.gigo.dev/api/search/bytes",
        json=p
    )

    if res.status_code != 200:
        return f"<api_error>\nFailed to retrieve bytes from GIGO API:\n({res.status_code}) {res.text}\n</api_error>"
    
    data = [
        {
            "url": f"https://www.gigo.dev/byte/{x['_id']}",
            "image": f"https://api.cdn.gigo.dev/static/bytes/t/{x['_id']}",
            "name": x["name"],
            "description": x["description_medium"],
            "language": ProgrammingLanguage.from_int(x["lang"]).value,
        } for x in res.json()['posts']
    ]
    return f"<api_response>\n{json.dumps(data)}\n</api_response>"


class JourneyUnitSearchParams(BaseModel):
    query: str = Field(..., description="Query that will be used to search for journey units. The query is searched both by keyword and semantic search.")
    language: Optional[ProgrammingLanguage] = Field(None, description="Filter results by programming language")


def search_journey_units(params: JourneyUnitSearchParams) -> str:
    p = {"query": params.query, "skip": 0, "limit": 10}
    if params.language:
        p["languages"] = [params.language.to_int()]
    
    res = requests.post(
        "https://api.cdn.gigo.dev/api/search/journeyUnits",
        json=p
    )

    if res.status_code != 200:
        return f"<api_error>\nFailed to retrieve journey units from GIGO API:\n({res.status_code}) {res.text}\n</api_error>"
    
    data = [
        {
            "url": f"https://www.gigo.dev/journey/info/{x['_id']}",
            "image": f"https://api.cdn.gigo.dev/static/junit/t/{x['_id']}",
            "name": x['name'],
            "description": x['description'],
            "languages": x['langs'],
        } for x in res.json()['units']
    ]
    return f"<api_response>\n{json.dumps(data)}\n</api_response>"


if __name__ == "__main__":
    # print(search_challenges(ChallengeSearchParams(query="start coding", language=ProgrammingLanguage.from_str("python"), renown=4, challenge_type=ChallengeType.Interactive)))
    # print(search_bytes(ByteSearchParams(query="concurrency", language=ProgrammingLanguage.from_str("rust"))))
    print(search_journey_units(JourneyUnitSearchParams(query="async", language=ProgrammingLanguage.from_str("python"))))

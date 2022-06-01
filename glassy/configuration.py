from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Protocol
from typing import Sequence
from typing import Tuple
from typing import Type

import marshmallow as msh
from ruamel.yaml import YAML

yaml = YAML(typ="safe")


CHECK_STRATEGIES: Tuple[str, ...] = ("http", "ping", "tcp", "command")

HTTP_VERBS: Tuple[str, ...] = ("get", "head", "post", "patch", "delete", "put")


class BaseSchema(msh.Schema):
    @dataclass
    class Container:
        pass

    @msh.post_load
    def _make_dataclass(self, data):
        return self.Container(**data)


class GlassyHTTPSettingsSerializer(BaseSchema):
    @dataclass
    class Container:
        url: str
        verb: str
        secure: bool
        username: Optional[str]
        password: Optional[str]
        codes: Sequence[int]

    url = msh.fields.Url(required=True)
    verb = msh.fields.String(validate=msh.validate.OneOf(HTTP_VERBS), missing="HEAD")
    secure = msh.fields.Boolean(missing=True)
    username = msh.fields.String(allow_none=True, missing=None)
    password = msh.fields.String(allow_none=True, missing=None)
    codes = msh.fields.List(
        msh.fields.Integer(validate=msh.validate.range(min=100, max=600)), missing=[200]
    )


class GlassyPingSettingsSerializer(BaseSchema):
    @dataclass
    class Container:
        address: str
        count: int
        timeout: int

    address = msh.fields.String(required=True)
    count = msh.fields.Integer(validate=msh.validate.Range(min=1), missing=5)
    timeout = msh.fields.Timeout(validate=msh.validate.Range(min=1), missing=5)


class GlassyTCPSettingsSerializer(BaseSchema):
    @dataclass
    class Container:
        address: str
        port: int

    address = msh.fields.String(required=True)
    port = msh.fields.Integer(
        validate=msh.validate.Range(min=1, max=65535), required=True
    )


class GlassyCommandSettingsSerializer(BaseSchema):
    @dataclass
    class Container:
        command: str
        args: Sequence[str]
        ok_codes: Sequence[int]
        warn_codes: Sequence[int]

    command = msh.fields.String(required=True)
    args = msh.fields.List(msh.fields.List(), missing=[])
    ok_codes = msh.fields.List(
        msh.fields.Integer(validate=msh.validate.Range(min=0)), missing=[0]
    )
    warn_codes = msh.fields.List(
        msh.fields.Integer(validate=msh.validate.Range(min=0)), missing=[]
    )


class GlassyCheckSerializer(BaseSchema):
    @dataclass
    class Container:
        name: Optional[str]
        slug: str
        strategy: str
        http: Optional[GlassyHTTPSettingsSerializer.Container]
        ping: Optional[GlassyPingSettingsSerializer.Container]
        tcp: Optional[GlassyTCPSettingsSerializer.Container]
        command: Optional[GlassyCommandSettingsSerializer.Container]
        dependents: Sequence[str]
        weight: int
        enabled: bool

    slug = msh.fields.String()
    strategy = msh.fields.String(
        validate=msh.validate.OneOf(CHECK_STRATEGIES), required=True
    )
    name = msh.fields.String(allow_none=True, missing=None)
    dependents = msh.fields.List(msh.fields.String(), missing=[])
    enabled = msh.fields.Boolean(missing=True)
    weight = msh.fields.Integer(missing=10)
    http = msh.fields.Nested(
        GlassyHTTPSettingsSerializer, missing=None, allow_none=True
    )
    ping = msh.fields.Nested(
        GlassyPingSettingsSerializer, missing=None, allow_none=True
    )
    tcp = msh.fields.Nested(GlassyTCPSettingsSerializer, missing=None, allow_none=True)
    command = msh.fields.Nested(
        GlassyCommandSettingsSerializer, missing=None, allow_none=True
    )

    @msh.pre_load
    def _set_slug(self, data: Dict[str, Any]) -> Dict[str, Any]:
        index = self.context.get("index", 0)
        data["slug"] = (
            f"{'%' if index < 10 else '%%'}{index}"
            if "slug" not in data
            else data["slug"]
        )

        return data

    @msh.validates_schema
    def _check_strategy(self, data: Dict[str, Any]):
        if data.get(data["strategy"]) is None:
            raise msh.ValidationError(
                f"Check item '{data.get('name', self.context.get('index', 0))}' has no settings for spceficied {data['strategy']} strategy"
            )


@dataclass
class GlassyStatusConfig:
    ok: str
    warn: str
    fail: str


@dataclass
class GlassyReplacementConfig:
    check: GlassyStatusConfig
    summary: GlassyStatusConfig

    @classmethod
    def build(cls, data: Dict[str, Any]):
        return cls(
            **{
                "check": GlassyStatusConfig(**data["check"])
                if "check" in data
                else GlassyStatusConfig(ok="███", warn="███", fail="███"),
                "summary": GlassyStatusConfig(**data["summary"])
                if "summary" in data
                else GlassyStatusConfig(
                    ok=" ONLINE ", warn="DEGRADED", fail="  FAULT   "
                ),
            }
        )


@dataclass
class GlassyConfig:
    replacements: GlassyReplacementConfig
    checks: List[GlassyCheckConfig]

    @classmethod
    def build(cls, data: Dict[str, Any]):
        replacements = GlassyReplacementConfig.build(data.get("replacements", {}))
        checks = [
            GlassyReplacementConfig.build(item, index)
            for index, item in enumerate(data.get("checks", []))
        ]

        names = [item.name for item in checks]
        if len(set(names)) != len(names):
            raise RuntimeError("Non-unique names")

        for check in checks:
            if any(dependent not in names for dependent in check.dependents):
                raise RuntimeError("unnamed dependent")

        return cls(replacements=replacements, checks=checks)


def load(path: Path) -> GlassyConfig:
    with path.open() as infile:
        data = yaml.load(infile)

    return GlassyConfig.build(data)

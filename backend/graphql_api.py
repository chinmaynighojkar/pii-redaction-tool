import asyncio
import os

import strawberry
from graphql import GraphQLError
from graphql.validation import NoSchemaIntrospectionCustomRule
from strawberry.extensions import AddValidationRules
from strawberry.fastapi import GraphQLRouter

import redactor

# The upload route bounds its input at 10 MB of file. A raw text argument has no
# such ceiling, so bound it here too: 50k characters is far past any realistic
# paste and well short of tying up the model on a single request.
MAX_TEXT_CHARS = 50_000

DEBUG = os.getenv("PII_DEBUG", "").lower() in {"1", "true", "yes"}


@strawberry.type
class Entity:
    type: str
    start: int
    end: int
    # The placeholder that replaced this span, never the value that was removed.
    redacted_text: str


@strawberry.type
class RedactionResult:
    redacted_text: str
    entities: list[Entity]


@strawberry.type
class Query:
    @strawberry.field
    def model_loaded(self) -> bool:
        """A schema needs a query root; this mirrors the REST /health check."""
        return redactor.MODEL_LOADED


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def redact_text(self, text: str) -> RedactionResult:
        """Redact PII in text.

        A mutation rather than a query even though nothing is mutated: the
        argument carries un-redacted PII, and GraphQL tooling never caches,
        GETs, or replays mutations.
        """
        if not redactor.MODEL_LOADED:
            raise GraphQLError("PII model failed to load on startup.")

        if len(text) > MAX_TEXT_CHARS:
            raise GraphQLError(f"Text too long. Maximum is {MAX_TEXT_CHARS} characters.")

        detected = await asyncio.to_thread(redactor.detect_pii, text)
        redacted, _summary = redactor.redact_text(text, detected)

        # The same spans redact_text worked from, rather than its summary, which
        # de-duplicates repeated values and so loses positions a caller needs to
        # highlight. Only the span and its label are exposed: the detector's own
        # "word" key holds the raw PII and never leaves this function.
        entities = [
            Entity(
                type=span["label"],
                start=span["start"],
                end=span["end"],
                redacted_text=redactor.redaction_placeholder(span["label"]),
            )
            for span in redactor.merge_adjacent(text, detected)
        ]

        return RedactionResult(redacted_text=redacted, entities=entities)


extensions = []
if not DEBUG:
    # Introspection hands an attacker the schema map; keep it to local dev.
    extensions.append(AddValidationRules([NoSchemaIntrospectionCustomRule]))

schema = strawberry.Schema(query=Query, mutation=Mutation, extensions=extensions)

graphql_router = GraphQLRouter(
    schema,
    graphql_ide="graphiql" if DEBUG else None,
    # Nothing in this schema may travel in a URL, where it would land in access
    # logs and browser history. Mutations already refuse GET; this covers queries.
    allow_queries_via_get=False,
)

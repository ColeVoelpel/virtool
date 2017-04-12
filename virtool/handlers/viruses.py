import pymongo
import pymongo.errors

from pprint import pprint
from aiohttp import web
from copy import deepcopy
from pymongo import ReturnDocument
from cerberus import Validator

import virtool.data_utils
import virtool.viruses
import virtool.history

from virtool.handlers.utils import unpack_json_request, json_response, bad_request, not_found, invalid_input, \
    protected, validation


CREATE_SCHEMA = {
    "name": {"type": "string", "required": True},
    "abbreviation": {"type": "string"}
}


EDIT_SCHEMA = {
    "name": {"type": "string"},
    "abbreviation": {"type": "string"}
}


CREATE_SEQUENCE_SCHEMA = {
    "accession": {"type": "string", "required": True},
    "definition": {"type": "string", "required": True},
    "host": {"type": "string"},
    "sequence": {"type": "string", "required": True}
}


EDIT_SEQUENCE_SCHEMA = {
    "host": {"type": "string"},
    "definition": {"type": "string"},
    "sequence": {"type": "string"}
}


async def find(req):
    """
    List truncated virus documents. Will take filters in URL parameters eventually.
     
    """
    documents = await req.app["db"].viruses.find({}, virtool.viruses.LIST_PROJECTION).to_list(length=10)

    return json_response([virtool.viruses.processor(document) for document in documents])


async def get(req):
    """
    Get a complete virus document. Joins the virus document with its associated sequence documents.

    """
    db = req.app["db"]

    virus_id = req.match_info["virus_id"]

    complete = await virtool.viruses.get_complete(db, virus_id)

    if not complete:
        return not_found()

    return json_response(complete)


@protected("modify_virus")
@validation(CREATE_SCHEMA)
async def create(req):
    """
    Add a new virus to the collection. Checks to make sure the supplied virus name and abbreviation are not already in
    use in the collection. Any errors are sent back to the client.

    """
    db, data = req.app["db"], req["data"]

    message = await virtool.viruses.check_name_and_abbreviation(db, data["name"], data.get("abbreviation", None))

    if message:
        return json_response({"message": message},  status=409)

    virus_id = await virtool.data_utils.get_new_id(db.viruses)

    data.update({
        "_id": virus_id,
        "last_indexed_version": None,
        "modified": True,
        "lower_name": data["name"].lower(),
        "isolates": [],
        "version": 0
    })

    await db.viruses.insert_one(data)

    joined = await virtool.viruses.join(db, virus_id, data)

    await virtool.history.add(
        db,
        "create",
        None,
        joined,
        ("Created virus ", data["name"], virus_id),
        req["session"].user_id
    )

    complete = await virtool.viruses.get_complete(db, virus_id)

    req.app["dispatcher"].dispatch(
        "viruses",
        "update",
        virtool.viruses.processor({key: joined[key] for key in virtool.viruses.LIST_PROJECTION})
    )

    return json_response(complete, status=201)


@protected("modify_virus")
@validation(EDIT_SCHEMA)
async def edit(req):
    """
    Edit an existing new virus. Checks to make sure the supplied virus name and abbreviation are not already in use in
    the collection.

    """
    db, data = req.app["db"], req["data"]

    virus_id = req.match_info["virus_id"]

    old = await virtool.viruses.join(db, virus_id)

    if not old:
        return not_found()

    name_change, abbreviation_change = data.get("name", None), data.get("abbreviation", None)

    message = await virtool.viruses.check_name_and_abbreviation(
        db,
        name_change,
        abbreviation_change
    )

    if message:
        return json_response({"message": message}, status=409)

    if name_change:
        data["lower_name"] = data["name"].lower()

    data["modified"] = True

    document = await db.viruses.find_one_and_update({"_id": virus_id}, {
        "$set": data,
        "$inc": {
            "version": 1
        }
    }, return_document=ReturnDocument.AFTER)

    new = await virtool.viruses.join(db, virus_id, document)

    description = None

    if name_change and abbreviation_change:
        description = ("Changed name and abbreviation to", new["name"], new["abbreviation"])
    elif name_change:
        description = ("Changed name to", new["name"])
    elif abbreviation_change:
        description = ("Changed abbreviation to", new["abbreviation"])

    await virtool.history.add(
        db,
        "edit",
        old,
        new,
        description,
        req["session"].user_id
    )

    req.app["dispatcher"].dispatch(
        "viruses",
        "update",
        virtool.viruses.processor({key: new[key] for key in virtool.viruses.LIST_PROJECTION})
    )

    return json_response(await virtool.viruses.get_complete(db, virus_id))


@protected("modify_virus")
async def remove(req):
    """
    Remove a virus document and its associated sequence documents.

    """
    db = req.app["db"]

    virus_id = req.match_info["virus_id"]

    # Join the virus.
    joined = await virtool.viruses.join(db, virus_id)

    if not joined:
        return not_found()

    # Remove all sequences associated with the isolates.
    await db.sequences.delete_many({"isolate_id": {"$in": virtool.viruses.extract_isolate_ids(joined)}})

    # Remove the virus document itself.
    await db.viruses.delete_one({"_id": virus_id})

    await virtool.history.add(
        db,
        "remove",
        joined,
        None,
        ("Removed virus", joined["name"], joined["_id"]),
        req["session"].user_id
    )

    req.app["dispatcher"].dispatch(
        "viruses",
        "remove",
        {"virus_id": virus_id}
    )

    return web.Response(status=204)


async def list_isolates(req):
    """
    Return a list of isolate records for a given virus. 
     
    """
    db = req.app["db"]

    virus_id = req.match_info["virus_id"]

    document = await db.viruses.find_one(virus_id, ["isolates"])

    if not document:
        return not_found()

    return json_response(document["isolates"])


async def get_isolate(req):
    """
    Get a complete specific isolate subdocument, including its sequences.
     
    """
    db = req.app["db"]

    virus_id = req.match_info["virus_id"]
    isolate_id = req.match_info["isolate_id"]

    document = await db.viruses.find_one({"_id": virus_id, "isolates.isolate_id": isolate_id}, ["isolates"])

    if not document:
        return not_found()

    isolate = [isolate for isolate in document["isolates"] if isolate["isolate_id"] == isolate_id][0]

    isolate["sequences"] = await db.sequences.find({"isolate_id": isolate["isolate_id"]}).to_list(None)

    return json_response(isolate)


@protected("modify_virus")
@validation(virtool.viruses.ISOLATE_SCHEMA)
async def add_isolate(req):
    """
    Add a new isolate to a virus.

    """
    db, data = req.app["db"], req["data"]

    virus_id = req.match_info["virus_id"]

    document = await db.viruses.find_one(virus_id)

    if not document:
        return not_found()

    isolates = deepcopy(document["isolates"])

    # True if the new isolate should be default and any existing isolates should be non-default.
    will_be_default = not isolates or data["default"]

    # Get the complete, joined entry before the update.
    old = await virtool.viruses.join(db, virus_id, document)

    # All source types are stored in lower case.
    data["source_type"] = data["source_type"].lower()

    # Get a unique isolate_id for the new isolate.
    isolate_id = await virtool.viruses.get_new_isolate_id(db)

    # Set ``default`` to ``False`` for all existing isolates if the new one should be default.
    if isolates and data["default"]:
        for isolate in isolates:
            isolate["default"] = False

    # Force the new isolate as default if it is the first isolate.
    if not isolates:
        data["default"] = True

    # Set the isolate as the default isolate if it is the first one.
    data.update({
        "default": will_be_default,
        "isolate_id": isolate_id
    })

    isolates.append(data)

    # Push the new isolate to the database.
    document = await db.viruses.find_one_and_update({"_id": virus_id}, {
        "$set": {
            "isolates": isolates,
            "modified": True
        },
        "$inc": {
            "version": 1
        }
    }, return_document=ReturnDocument.AFTER)

    # Get the joined entry now that it has been updated.
    new = await virtool.viruses.join(db, virus_id, document)

    isolate_name = virtool.viruses.format_isolate_name(data)

    description = ("Added isolate", isolate_name, isolate_id)

    if will_be_default:
        description += tuple(("as default",))

    await virtool.history.add(
        db,
        "add_isolate",
        old,
        new,
        description,
        req["session"].user_id
    )

    return json_response(data, status=201)


@protected("modify_virus")
@validation(virtool.viruses.ISOLATE_SCHEMA)
async def edit_isolate(req):
    """
    Edit an existing isolate.

    """
    db, data = await unpack_json_request(req)

    if not data:
        return bad_request("Empty input")

    v = Validator({
        "source_type": {"type": "string"},
        "source_name": {"type": "string"},
        "default": {"type": "boolean", "allowed": [True]}
    })

    if not v(data):
        return invalid_input(v.errors)

    data = v.document

    virus_id = req.match_info["virus_id"]
    isolate_id = req.match_info["isolate_id"]

    document = await db.viruses.find_one(virus_id)

    if not document:
        return not_found()

    # All source types are stored in lower case.
    if "source_type" in data:
        data["source_type"] = data["source_type"].lower()

    isolates = deepcopy(document["isolates"])

    # Set ``default`` to ``False`` for all existing isolates if the new one should be default.
    if data.get("default", False):
        for isolate in isolates:
            isolate["default"] = False

    isolate = virtool.viruses.find_isolate(isolates, isolate_id)

    isolate.update(data)

    old = await virtool.viruses.join(db, virus_id)

    # Push the new isolate to the database.
    document = await db.viruses.find_one_and_update({"_id": virus_id}, {
        "$set": {
            "isolates": isolates,
            "modified": True
        }
    }, return_document=ReturnDocument.AFTER)

    # Get the joined entry now that it has been updated.
    new = await virtool.viruses.join(db, virus_id, document)

    isolate_name = virtool.viruses.format_isolate_name(isolate)

    if "source_type" in data or "source_name" in data:
        description = ("Renamed isolate to", isolate_name, isolate_id)

        if data.get("default", False):
            description += tuple(("and set as default",))
    else:
        description = ("Set", isolate_name, isolate_id, "as default")

    # Use the old and new entry to add a new history document for the change.
    await virtool.history.add(
        db,
        "edit_isolate",
        old,
        new,
        description,
        req["session"].user_id
    )

    return json_response(isolate, status=200)


@protected("modify_virus")
async def remove_isolate(req):
    """
    Remove an isolate and its sequences from a virus.

    """
    db = req.app["db"]

    virus_id = req.match_info["virus_id"]

    document = await db.viruses.find_one(virus_id)

    if not document:
        return not_found()

    isolates = deepcopy(document["isolates"])

    isolate_id = req.match_info["isolate_id"]

    # Get any isolates that have the isolate id to be removed (only one should match!).
    isolate_to_remove = virtool.viruses.find_isolate(isolates, isolate_id)

    # Remove the isolate from the virus' isolate list.
    isolates.remove(isolate_to_remove)

    new_default = None

    # Set the first isolate as default if the removed isolate was the default.
    if isolate_to_remove["default"] and len(isolates):
        new_default = isolates[0]
        new_default["default"] = True

    old = await virtool.viruses.join(db, virus_id, document)

    document = await db.viruses.find_one_and_update({"_id": virus_id}, {
        "$set": {
            "isolates": isolates,
            "modified": True
        }
    }, return_document=ReturnDocument.AFTER)

    new = await virtool.viruses.join(db, virus_id, document)

    # Remove any sequences associated with the removed isolate.
    await db.sequences.delete_many({"isolate_id": isolate_id})

    description = (
        "Removed isolate",
        virtool.viruses.format_isolate_name(isolate_to_remove),
        isolate_to_remove["isolate_id"]
    )

    if isolate_to_remove["default"] and new_default:
        description += (
            "and set",
            virtool.viruses.format_isolate_name(new_default), new_default["isolate_id"],
            "as default"
        )

    await virtool.history.add(
        db,
        "remove_isolate",
        old,
        new,
        description,
        req["session"].user_id
    )

    return web.Response(status=204)


async def list_sequences(req):
    db = req.app["db"]

    virus_id = req.match_info["virus_id"]
    isolate_id = req.match_info["isolate_id"]

    if not await db.viruses.find({"_id": virus_id}, {"isolates.isolate_id": isolate_id}).count():
        return not_found()

    documents = await db.sequences.find({"isolate_id": isolate_id}, virtool.viruses.sequence_projection).to_list(None)

    return json_response([virtool.viruses.sequence_processor(d) for d in documents])


async def get_sequence(req):
    """
    Get a single sequence document by its ``accession`.
     
    """
    db = req.app["db"]

    accession = req.match_info["accession"]

    document = await db.sequences.find_one(accession, virtool.viruses.sequence_projection)

    if not document:
        return not_found()

    return json_response(virtool.viruses.sequence_processor(document))


@protected("modify_virus")
@validation(CREATE_SEQUENCE_SCHEMA)
async def create_sequence(req):
    """
    Create a new sequence record for the given isolate.
     
    """
    db, data = req.app["db"], req["data"]

    virus_id, isolate_id = (req.match_info[key] for key in ["virus_id", "isolate_id"])

    data.update({
        "_id": data.pop("accession"),
        "isolate_id": isolate_id,
        "host": data["host"] or ""
    })

    old = await virtool.viruses.join(db, virus_id)

    if not old:
        return not_found()

    try:
        await db.sequences.insert_one(data)
    except pymongo.errors.DuplicateKeyError:
        return json_response({"message": "Accession already exists"}, status=409)

    new = await virtool.viruses.join(db, virus_id)

    isolate = virtool.viruses.find_isolate(old["isolates"], isolate_id)

    await virtool.history.add(
        db,
        "create_sequence",
        old,
        new,
        ("Created new sequence", data["_id"], "in isolate", virtool.viruses.format_isolate_name(isolate), isolate_id),
        req["session"].user_id
    )

    return json_response(virtool.viruses.sequence_processor(data))


@protected("modify_virus")
@validation(EDIT_SEQUENCE_SCHEMA)
async def edit_sequence(req):
    db, data = req.app["db"], req["data"]

    virus_id, isolate_id, accession = (req.match_info[key] for key in ["virus_id", "isolate_id", "accession"])

    data["_id"] = data.pop("accession")

    sequence_document = await db.sequences.update_one({"_id": accession}, {
        "$set": data
    })

    if not sequence_document:
        return not_found()

    return json_response(virtool.viruses.sequence_processor(sequence_document))


async def remove_sequence(req):
    db = req.app["db"]

    accession = req.match_info["accession"]

    document = await db.sequences.find_one(accession, virtool.viruses.sequence_projection)

    if not document:
        return not_found()

    return json_response(virtool.viruses.sequence_processor(document))


async def list_history(req):
    db = req.app["db"]

    virus_id = req.match_info["virus_id"]

    if not await db.viruses.find({"_id": virus_id}).count():
        return not_found()

    documents = await db.history.find({"virus_id": virus_id}).to_list(None)

    return json_response(documents)

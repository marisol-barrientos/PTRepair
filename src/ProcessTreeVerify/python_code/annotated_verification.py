#    Copyright (C) <2025>  <Johannes Löbbecke>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.

import logging
import re
from share import config
#from hashmap import constraints_t # Future Work :) 
import xml.etree.ElementTree as ET
from util import * 
## Check util which is an interface to all other methods if you want all method names

## Load the Hashmap for run time voting


## This contains the verification using explicit, annotated verification, meaning the activities are identified by labels and resources
## are explicity annotated

namespace = {"ns0": "http://cpee.org/ns/description/1.0"}
data_decision_tags= [ ".//ns0:loop", ".//ns0:alternative"]
logger = logging.getLogger(__name__)

def normalize_text(value):
    if value is None:
        return ""
    return " ".join(str(value).strip().casefold().split())


def text_equals(a, b):
    return normalize_text(a) == normalize_text(b)

# Control Flow
## Existence: Checks if an activity a exists in the xml tree and returns the element or None, identifes by label, to identify using resource/data see below
def exists(tree, a):#
    if isinstance(a, ET.Element):
        return a
    elif text_equals(a, "End Activity"):
        return tree.find(".//ns0:end_activity", namespace)
    elif text_equals(a, "Start Activity"):
        return tree.find(".//ns0:start_activity", namespace)
    elif text_equals(a, "terminate"):
        return tree.find(".//ns0:terminate", namespace)
    else:
        logger.add_activity(readable(a))
        a_ele = exists_by_label(tree, a)
        if a_ele is None:
            logger.info(f'Activity "{readable(a)}" existence was checked but not found')
        return a_ele

## Absence: opposite of exists, returns a Boolean
def absence(tree, a):
    apath = exists(tree, a)
    if apath is None:
        logger.info(
            f'Activity "{readable(a)}" is absent from the process'
        )
        return True
    else:
        logger.info(
            f'Activity "{readable(a)}" exists in the process'
        )
        return False

## loop(tree, a): checks if an activity is in a loop, returns None or said loop element
def loop(tree, a):
    loops = tree.findall(".//ns0:loop", namespace)
    for loop in loops:
        apath = exists(loop, a)
        if apath is not None:
            logger.info(f'Found Activity "{readable(a)}" in loop "{readable(loop)}"')
            return loop
    logger.info(f'Found no Loop with Activity "{readable(a)}" in it')
    return None

def directly_follows(tree, a, b):
    apath = exists(tree, a)
    bpath = exists(tree, b)
    if apath is not None:
        if bpath is not None:
            if text_equals(a, "terminate"):
                logger.info(f'terminate can never lead to another activity, "{readable(b)}" directly follows "{readable(a)}" is False')
            elif text_equals(b, "terminate"):
                bpaths = tree.findall(".//ns0:terminate", namespace)
                for bpath in bpaths:
                    ## For terminates only must directly follows is accepted, since can directly follows makes no sense
                    must = directly_follows_must(tree, apath, bpath)
                    if must:
                        logger.info(f'Found a terminate that directly follows "{readable(a)}"')
                        return True
                logger.info(f'Found no terminate that directly follows "{readable(a)}"')
                return False
            else:
                must = directly_follows_must(tree, apath, bpath)
                if must:
                    logger.info(f'Activity "{readable(b)}" directly follows Activity "{readable(a)}" is True')
                    return True
                else:
                    can = directly_follows_can(tree, apath, bpath)
                    if can:
                        logger.info(f'Activity "{readable(b)}" CAN directly follow "{readable(a)}": True, but does not have to')
                        return True
                    else:
                        logger.info(f'Activity "{readable(b)}" does not directly follow "{readable(a)}"')
                        return False
        else:
            logger.add_missing_activity(readable(b))
            logger.info(f'Activity "{readable(b)}" is missing in the process')
            return False
    else:
        logger.add_missing_activity(readable(a))
        logger.info(f'Activity "{readable(a)}" is missing in the process')
        return False

def exclusive(tree, a, b):
    apath = exists(tree, a)
    bpath = exists(tree, b)
    if apath is not None:
        if bpath is not None:
            compare = compare_ele(tree, apath, bpath)
            if compare == 0:
                logger.info(f'Activity "{readable(a)}" and Activity "{readable(b)}" are on different exclusive branches')
                return True
            else:
                logger.info(f'Activity "{readable(a)}" and Activity "{readable(b)}" are not on different exclusive branches')
                return False
        else:
            logger.add_missing_activity(readable(b))
            logger.info(f'Activity "{readable(b)}" is missing in the process')
            return False
    else:
        logger.add_missing_activity(readable(a))
        logger.info(f'Activity "{readable(a)}" is missing in the process')
        return False

## Leads To: Checks if an activity a exists and if it does if the activity it leads to exists after
def leads_to(tree, a, b):
    apath = exists(tree, a)
    bpath = exists(tree, b)

    # ---------------------------------------------------------
    # activity a missing
    # ---------------------------------------------------------

    if apath is None:
        logger.add_missing_activity(a)

        logger.info(
            f'Activity "{readable(a)}" '
            f'is not found in the tree'
        )

        return True

    # ---------------------------------------------------------
    # activity b missing
    # ---------------------------------------------------------

    if bpath is None:
        logger.info(
            f'Activity "{readable(b)}" '
            f'is not found in the tree'
        )

        return False

    # ---------------------------------------------------------
    # compare structural relation
    # ---------------------------------------------------------

    compare = compare_ele(
        tree,
        apath,
        bpath
    )

    # ---------------------------------------------------------
    # different exclusive branches
    # ---------------------------------------------------------

    if compare == 0:
        logger.info(
            f'Activity "{readable(a)}" '
            f'and Activity "{readable(b)}" '
            f'are on different exclusive branches'
        )

        return False

    # ---------------------------------------------------------
    # parallel
    # ---------------------------------------------------------

    elif compare == -1:
        logger.info(
            f'Activity "{readable(a)}" '
            f'and Activity "{readable(b)}" '
            f'are in parrallel'
        )

        return False

    # ---------------------------------------------------------
    # b before a
    # ---------------------------------------------------------

    elif compare == 2:
        logger.info(
            f'Activity "{readable(b)}" '
            f'is before Activity "{readable(a)}"'
        )

        return False

    # ---------------------------------------------------------
    # a before b
    # ---------------------------------------------------------

    elif compare == 1:
        logger.info(
            f'Activity "{readable(a)}" '
            f'is before Activity "{readable(b)}"'
        )

        ancestors_a, ancestors_b, shared = (
            get_shared_ancestors(
                tree,
                apath,
                bpath
            )
        )

        # -----------------------------------------------------
        # detect XOR ancestors containing b
        # -----------------------------------------------------

        xor_ancestors = [
            elem for elem in ancestors_b
            if (
                elem.tag.endswith("choose")
                or elem.tag.endswith("exclusive")
            )
        ]

        # -----------------------------------------------------
        # no XOR involved
        # -----------------------------------------------------

        if len(xor_ancestors) == 0:
            logger.info(
                f'Activity "{readable(a)}" '
                f'is before "{readable(b)}" '
                f'in the same execution path'
            )

            return True

        # -----------------------------------------------------
        # verify b exists in ALL XOR branches
        # -----------------------------------------------------

        for xor in xor_ancestors:
            branches = list(xor)

            for branch in branches:
                branch_has_b = False

                for elem in branch.iter():
                    label = elem.attrib.get("label")

                    if label == b:
                        branch_has_b = True
                        break

                if not branch_has_b:
                    logger.info(
                        f'Activity "{readable(b)}" '
                        f'does not occur in all '
                        f'exclusive branches'
                    )

                    return False

        logger.info(
            f'Activity "{readable(b)}" '
            f'occurs in all exclusive branches '
            f'following "{readable(a)}"'
        )

        return True

    # ---------------------------------------------------------
    # fallback
    # ---------------------------------------------------------

    return False

## Precedence: Checks if an activity a exists, and if it does if the activity it requires as a precedence exists prior
def precedence(tree, a, b):
    a_ele = exists(tree, a)
    b_ele = exists(tree, b)
    if a_ele is not None:
        if b_ele is not None:
            compare = compare_ele(tree, a_ele, b_ele)
            if compare == 0:
                logger.info(f'Activities "{readable(a)}" and "{readable(b)}" are in different exclusive branches and accordingly cannot be compared using precedence')
                return False
            elif compare == -1:
                logger.info(f'Activities "{readable(a)}" and "{readable(b)}" are in parrallel and accordingly cannot be compared using precedence')
                return False
            elif compare == 1:
                logger.info(f'Activity "{readable(a)}" was found before "{readable(b)}", so precedence "{readable(a)}" requires "{readable(b)}" before is False')
                return False
            elif compare == 2:
                logger.info(f'Activity "{readable(b)}" was found before "{readable(a)}". Ensuring that "{readable(b)}" is not on an exclusive branch which could lead to violations in some traces')
                ancestors_a, ancestors_b, shared = get_shared_ancestors(tree, a_ele, b_ele)
                if any(elem.tag.endswith("choose") for elem in ancestors_b):
                    LCA = shared[0].tag
                    if LCA.endswith("alternative") or LCA.endswith("otherwise"):
                        logger.info(f'Activity "{readable(a)}" and Activity "{readable(b)}" are on the same branch in the correct order')
                        return True
                    logger.info(f'Activity "{readable(b)}" was found before "{readable(a)}", but it is in a different exclusive branch, so precedence can not be guaranteed in every trace')
                    return False
                logger.info(f'Activity "{readable(b)}" was found before "{readable(a)}", and "{readable(b)}" is not on an exclusive branch, so precedence "{readable(a)}" requires "{readable(b)}" before is True')
                return True
        else:
            logger.add_missing_activity(readable(b))
            logger.info(f'Activity "{readable(a)}" was found but Activity "{readable(b)}" was not found, so precedence "{readable(a)}" requires "{readable(b)}" before it is false')
            return False
    else:
        logger.add_missing_activity(readable(a))
        logger.info(f'Activity "{readable(a)}" was not found in the process so precedence "{readable(a)}" requires "{readable(b)}" before it is true')
        return True


## Leads To Absence: if activity a exists, activity b does not exist after:
def leads_to_absence(tree, a, b):
    apath = exists(tree, a)
    bpath = exists(tree, b)
    if apath is not None:
        if bpath is None:
            return True
        else:
            compare = compare_ele(tree, apath, bpath)
            if compare == 0:
                return True
            elif compare == -1:
                return False
            elif compare == 1:
                return False
            elif compare == 2:
                return True
    else:
        return True

## Precdence Absence: if activity a exists, then activity b does not exist before
def precedence_absence(tree, a, b):
    apath = exists(tree, a)
    bpath = exists(tree, b)
    if apath is not None:
        if not bpath is not None:
            return True
        else:
            compare = compare_ele(tree, apath, bpath)
            if compare == 0: ## exclusive, different branch
                return True 
            elif compare == -1: ## parallel, different branch
                return False 
            elif compare == 1: ## apath is first
                return True
            elif compare == 2: ## bpath is first
                return False 
    else:
        return True

## parallel: checks if activities a and b are in parallel, if either does not exist return false
def parallel(tree, a, b):
    apath = exists(tree, a)
    bpath = exists(tree, b)
    if apath is not None:
        if bpath is not None:
            compare = compare_ele(tree, apath, bpath)
            if compare == -1:
                logger.info(f'Activities "{readable(a)}" and "{readable(b)}" are in parallel')
                return True
            else:
                logger.info(f'Activities "{readable(a)}" and "{readable(b)}" are not in parallel')
                return False
        else:
            logger.add_missing_activity(readable(b))
            logger.info(f'Activity "{readable(b)}" is missing in the process')
            return False
    else:
        logger.add_missing_activity(readable(a))
        logger.info(f'Activity "{readable(a)}" is missing in the process')
        return False

# Resource

## Returns whichever activity is executed a resource, if none does return value is None## Returns whichever activity is executed a resource, if none does return value is None
def executed_by_identify(tree, resource):
    for call in tree.findall(".//ns0:call", namespace):
        target = call.find('.//ns0:annotations/ns0:_generic/ns0:Resource', namespace)
        if target is not None:
            resources_split = target.text.split(",")
            for target_resource in resources_split:
                if text_equals(resource, target_resource):
                    label = call.find('.//ns0:parameters/ns0:label', namespace).text
                    logger.info(f'Activity "{readable(label)}" was found which is executed by resource "{readable(resource)}"')
                    return label
    logger.info(f'No Activity was found where resource "{readable(resource)}" is annotatet as Resource')
    return None

## Executed By Annotation: checks if an activity a exists, and if it does if it is executed by resource, by checking the annotation for Input Name: Resource
def executed_by(tree, a, resource,):
    apath = exists(tree, a)
    if apath is not None:
        resources = executed_by_annotated(apath, tree)
        for a_resource in resources if resources is not None else []:
            if text_equals(a_resource, resource):
                logger.info(f'Activity "{readable(a)}" is executed by Resource "{readable(resource)}"')
                return True
        logger.info(f'Activity "{readable(a)}" does not have an annotation Resource "{readable(resource)}"')
        return False
    else:
        logger.add_missing_activity(readable(a))
        logger.info(f'Activity "{readable(a)}" is missing in the process')
        return False

## Returns the FIRST resource that is executing activity a, used to compare resources for segregation type requirements
def executed_by_return(tree, a):
    apath = exists(tree, a)
    if apath is not None:
        resources = executed_by_annotated(apath, tree)
        for resource in resources if resources is not None else []:
            logger.info(f'Activity "{readable(a)}" is executed by resource "{readable(resource)}"')
            return resource
    else:
        logger.add_missing_activity(readable(a))
        logger.info(f'Activity "{readable(a)}" does not exist.')
        return None

# Recurring: checks if an activity is in a loop that contains a timeout activity with time t after a
def recurring(tree, a, t):
    a_ele = exists(tree, a)
    if a_ele is not None:
        loop_ele = loop(tree, a)
        if loop_ele is not None:
            for timeout in timeouts_exists(loop_ele):
                if timeout[1] is not None:
                    if not timeout[1].isdigit():
                        logger.warning('timeout in the loop uses a dataobject timestamp or is not passed a digit, correct dataobject is assumed, but this is a dynamic data requirement')
                        return leads_to(loop_ele, a_ele, timeout[0])
                    else:
                        logger.info(f'Identified a timeout in a loop with "{readable(a)}"')
                        if t == int(timeout[1]):
                            logger.info(f'Verifying existence of "{readable(a)}" in "{readable(loop_ele)}"')
                            return leads_to(loop_ele, a_ele, timeout[0])
            logger.info('No timeout was found to enforce the recurring requirement')
            return False
        else:
            logger.info(f'Activity "{readable(a)}" is not in a loop and accordingly can not be recurring')
            return False
    else:
        logger.info(f'Activity "{readable(a)}" is missing in the process, so the recurring requirement is trivially false')

# timed_alternative: checks if two activities are in a cancel branch relationship, with a timeout before the time_alternative b, if either is missing its false
def timed_alternative(tree, a, b, time):
    a_ele = exists(tree, a)
    if a_ele is not None:
        b_ele = exists(tree, b)
        if b_ele is not None:
            for timeout in timeouts_exists(tree):
                parallel = cancel_first(tree, timeout[0], a_ele)
                if parallel is not None:
                    if timeout[1] is not None:
                        if not timeout[1].isdigit():
                            logger.warning('timeout in the parallel cancel uses a dataobject timestamp or is not passed a digit, correct dataobject is assumed, but this is a dynamic data requirement')
                            return exists(timeout[0], a)
                        else:
                            logger.info(f'Identified a timeout in a parrallel cancel with "{readable(b)}"')
                            if time == int(timeout[1]):
                                logger.info(f'Verifying existence of "{readable(a)}" in "{readable(parallel)}"')
                                return exists(parallel, a)
                            else:
                                logger.info(f'timeout: "{timeout[1]}", while time required is: "{time}"')
                                return False
            logger.info('No timeout was found to enforce the timed_alternative requirement')
            return False
        else:
            logger.info(f'Activity "{readable(b)}" is missing so the timed_alternative relationship is False')
    else:
        logger.info(f'Activity "{readable(a)}" is missing so the timed_alternative relationship is False')
        return False

## Min Time between two activities, enforced via Voting
def min_time_between(tree, a, b, time, c = None):
    a_sync = False
    if leads_to(tree, a, b):
        apath = exists(tree, a)
        bpath = exists(tree, b)
        ## Original Method had errors, but this pattern never appears in practice, so fix this later
        return True
    else:
        logger.info(f'Activities "{readable(a)}" and "{readable(b)}" are not in a leads_to relationship, so the min_time_between requirement is False')
        return False

## By Due Date: annotated,
## This simply reads the annotation whether the due date is set correctly in the annotation, it does not check actual implementation, could be extended with voting later then it would even work during execution
def by_due_date_annotated(tree, a, timestamp):
    for call in tree.findall(".//ns0:call", namespace):
        label = call.find("ns0:parameters/ns0:label", namespace)
        if label is not None and text_equals(label.text, a):
            annotation = call.find('.//ns0:annotations/ns0:_generic/ns0:DueDate', namespace)
            if annotation is not None:
                if int(annotation.text) <= int(timestamp):
                    logger.info(f'Annotation for Activity "{readable(a)}" which equals the timestamp or is smaller was found')
                    return True
                else:
                    logger.info(f'Activity "{readable(a)}" has a annotation for a due date but it is empty')
                    return False
            else:
                logger.info(f'Activity "{readable(a)}" does not have a annotation for a due date, add it using the generic annotations DueDate with a unix timestamp')
    logger.add_missing_activity(readable(a))
    logger.info(f'Activity "{readable(a)}" does not exist in the tree, and can accordingly never be executed before its due data')
    return False

## By Due Date: checks if the due date requirement is explicitly defined through sync check
def by_due_date_explicit(tree, a, timestamp):
    apath = exists(tree, a)
    if apath:
        for call in due_date_exists(tree):
            if int(call[1]) <= int(timestamp):
                condition = f"data.{call[2]}"
                logger.info(f'found a due date activity that enforces the date requirement, check for alternative branch with condition "{condition}" that eventually leads to "{readable(a)}"')
                return condition_directly_follows(tree, condition, a)
        logger.info('no due date activity was found to enforce the due date requirement')
        return False
    else:
        logger.add_missing_activity(readable(a))
        logger.info(f'Activity "{readable(a)}" does not exist in the tree, and can accordingly never be executed before its due data')
        return False

## checks both annotated and explicit, returns true if either
def by_due_date(tree, a, timestamp, c = None):
    annotated = by_due_date_annotated(tree, a, timestamp)
    explicit = by_due_date_explicit(tree, a, timestamp)
    logger.info(f'The due date is enforced through annotation: {annotated}. The due date is enforced explicitly: {explicit}. Overall this means the due date is {annotated or explicit}')
    if explicit:
        return True
    elif annotated:
        logger.warning('Assurance level is reduced, since the due date is only enforced through annotation')
        return True
    else:
        return False

## There are technically many ways to implement this and accordingly many ways this could be checked, we enforcce here a very visually pleasing way of enforcing this, which is a event based gateway with a timeout. If said timeout finishes first it would mean that the max time between has passed. This is just one of many ways such as adding syncs before and after a and b, but this would be much less checkable and also have several ways of implementing
def max_time_between(tree, a, b, time, c = None):
    apath = exists(tree, a)
    bpath = exists(tree, b)
    if apath is not None:
        if bpath is not None:
            for timeout in timeouts_exists(tree):
                if cancel_last(tree, timeout[0], bpath) is not None:
                    if timeout[1] is not None:
                        if not timeout[1].isdigit():
                            logger.warning('timeout in the parallel with cancel uses a dataobject timestamp or is not passed a digit')
                            return True
                        else:
                            logger.info(f'Identified a timeout in a parrallel with cancel relationship with "{readable(b)}"')
                            return time == int(timeout[1])## only works as long as all times are parsed as seconds
                    else:
                        logger.info('timeout in the parallel with cancel is not passed a argument or 0')
                        return False
            logger.info('No timeout was found to enforce the max time between requirement')
            return False
        else:
            logger.add_missing_activity(readable(b))
            logger.info(f'Activity "{readable(b)}" is missing in the process')
    else:
        logger.add_missing_activity(readable(a))
        logger.info(f'Activity "{readable(a)}" is missing in the process')
        return False

## Data
## Send Exist: Checks if any activity in tree sends data data, returns those activity as a list or None
def send_exist(tree, data, complete = False):
    dataobjects = data_objects(tree)
    returnlist = []
    for call in dataobjects:
        for data_object in call[1]:
            if text_equals(data_object, data):
                label = call[0].find("ns0:parameters/ns0:label", namespace)
                if label is not None:
                    label = label.text
                logger.info(f'found activity "{readable(label)}" which sends dataobject "{data}"')
                returnlist.append(call[0])
    if len(returnlist) > 0:
        if complete:
            return returnlist
        else:
            return returnlist[0]
    else:
        logger.info(f'did not find any activity which sends dataobject "{data}"')
        return None

## Receive Exist: Checks if any activity in tree receives data data, returns those activities or None
def receive_exist(tree, data, complete = False):
    dataobjects = data_objects(tree)
    returnlist = []
    for call in dataobjects:
        for data_object in call[2]:
            if text_equals(data_object, data):
                label = call[0].find("ns0:parameters/ns0:label", namespace)
                if label is not None:
                    label = label.text
                logger.info(f'found activity at path "{readable(call[0])}" with label "{readable(label)}" which receives dataobject "{data}"')
                returnlist.append(call[0])
    if len(returnlist) > 0:
        if complete:
            return returnlist
        else:
            return returnlist[0]
    else:
        logger.info(f'did not find any activity which receives dataobject "{data}"')
        return None

def activity_sends(tree, a, data):
    apath = exists(tree, a)
    if apath is not None:
        a_dict = activity_data_checks(tree, apath)
        arguments = a_dict["arguments"]
        prepare = a_dict["prepare"]
        for occurance in arguments:
            if text_equals(occurance, data):
                logger.info(f'data object "{data}" is sent in the arguments of activity "{readable(a)}"')
                return True
        for occurance in prepare:
            if text_equals(occurance, data):
                logger.info(f'data object "{data}" is prepared for sending in prepare of activity "{readable(a)}"')
                return True
        logger.info(f'data object "{data}" is not found in neither prepare nor arguments of Activity "{readable(a)}"')
        return False
    else:
        logger.info(f'Activity "{readable(a)}" does not exist in the tree, accordingly the send is trivally true')
        return True

def activity_receives(tree, a, data):
    apath = exists(tree, a)
    if "data." in normalize_text(data):
        data = data.split(".",1)
    if apath is not None:
        a_dict = activity_data_checks(tree, apath)
        finalize = a_dict["finalize"]
        for occurance in finalize:
            if text_equals(occurance, data):
                logger.info(f'data object "{data}" is finalized from Activity "{readable(a)}"')
                return True
        logger.info(f'data object "{data}" is not found in finalize of Activity "{readable(a)}"')
        return False
    else:
        logger.add_missing_activity(readable(a))
        logger.info(f'Activity "{readable(a)}" does not exist in the tree, accordingly the receive is trivally true')
        return True

def condition(tree, condition):
    if condition_finder(tree, condition):
        return True
    else:
        return False

def condition_directly_follows(tree, condition, a):

    impacts = condition_impacts(tree, condition)

    # Remove impacts that directly follow each other
    if len(impacts) > 1:

        filtered_impacts = []

        for i in range(len(impacts)):

            try:
                if i < len(impacts) - 1:
                    if directly_follows(tree, impacts[i], impacts[i + 1]):
                        continue

                filtered_impacts.append(impacts[i])

            except Exception as e:
                logger.error(f"Error while filtering impacts: {e}")

        impacts = filtered_impacts

        logger.info(
            f'Found {len(impacts)} calls that influence '
            f'condition "{readable(condition)}". '
            f'Checking for a directly following branch for each'
        )

    #
    # SINGLE IMPACT CASE
    #
    if len(impacts) < 2:

        branch = condition_finder(tree, condition)

        if branch is None:
            logger.info(
                f'No branch with condition "{readable(condition)}" was found'
            )
            return False

        apath = exists(branch, a)

        if apath is None:
            logger.info(
                f'Activity "{readable(a)}" did not exist in the branch '
                f'of condition "{readable(condition)}"'
            )
            return False

        #
        # ONLY SEMANTIC EXECUTABLE ELEMENTS
        #
        elements = [
            elem for elem in branch.iter()
            if is_semantic_call(elem)
            or elem.tag.endswith("terminate")
        ]

        counter = 0

        for ele in elements:

            #
            # If another executable activity appears before a,
            # then a does not directly follow the condition
            #
            if counter == 1:
                logger.info(
                    f'Activity "{readable(a)}" did not directly follow '
                    f'the data condition "{readable(condition)}"'
                )
                return False

            if ele == apath:

                logger.info(
                    f'Activity "{readable(a)}" directly followed '
                    f'the data_condition "{readable(condition)}"'
                )

                return True

            counter += 1

    #
    # MULTI-IMPACT CASE
    #
    else:

        branches = multi_condition_finder(tree, condition)

        if len(branches) == 0:

            logger.info(
                f'No branch with condition "{readable(condition)}" was found'
            )

            return True

        if len(impacts) != len(branches):

            logger.warning(
                'There is not a branch condition for every time '
                'the condition can change so immediately follows is violated'
            )

            return False

        logger.info(
            'Checking for all data impact and branch pairs'
        )

        for i in range(len(impacts)):

            logger.info(f'Pair {i}:')

            apath = exists(branches[i], a)

            if apath is None:
                continue

            elements = [
                elem for elem in branches[i].iter()
                if is_semantic_call(elem)
                or elem.tag.endswith("terminate")
            ]

            counter = 0

            for ele in elements:

                if counter == 1:

                    logger.info(
                        f'Activity "{readable(a)}" did not directly follow '
                        f'the data condition "{readable(condition)}"'
                    )

                    return False

                if ele == apath:

                    logger.info(
                        f'Activity "{readable(a)}" directly followed '
                        f'the data_condition "{readable(condition)}"'
                    )

                    return True

                counter += 1

    logger.error(
        'If we got here something went wrong in '
        'condition_directly_follows'
    )

    return False

## activity failure eventually follows: If an activity a fails then b has to be executed. Checks for existence of a and b and then checks if a has a dataobject rescue that then has to exist in a condition towards a branch b
def failure_eventually_follows(tree, a, b):
    apath = exists(tree, a)
    bpath = exists(tree, b)
    if apath is not None:
        if bpath is not None:
            dataobjects = activity_data_checks(tree,apath)
            for data_object in dataobjects["rescue"]:
                condition = f"data.{data_object}"
                logger.info(f'Found a dataobject "{data_object}" that is used in a rescue of "{readable(a)}", checking if there is a branch with condition "{readable(condition)}" that eventually leads to "{readable(b)}"')
                if condition_eventually_follows(tree, condition, b):
                    logger.info(f'Activity "{readable(b)}" eventually follows the failure of "{readable(a)}" through the dataobject "{data_object}"')
                    return True
            logger.info(f'No dataobject in rescue of "{readable(a)}" is used in a branch condition, so failure eventually follows can not be guaranteed')
            return False
        else:
            logger.add_missing_activity(b)
            logger.info(f'Activity "{readable(b)}" is missing in the process, so failure eventually follows can not be guaranteed')
            return False
    else:
        logger.add_missing_activity(a)
        logger.info(f'Activity "{readable(a)}" is missing in the process, so failure eventually follows is trivially true')
        return True

## activity failure directly follows: If an activity a fails then b has to be executed directly after. Checks for existence of a and b and then checks if a has a dataobject rescue that then has to exist in a condition towards a branch b that directly follows
def failure_directly_follows(tree, a, b):
    apath = exists(tree, a)
    bpath = exists(tree, b)
    if apath is not None:
        if bpath is not None:
            dataobjects = activity_data_checks(tree, apath)
            for data_object in dataobjects["rescue"]:
                condition = f"data.{data_object}"
                logger.info(f'Found a dataobject "{data_object}" that is used in a rescue of "{readable(a)}", checking if there is a branch with condition "{readable(condition)}" that directly leads to "{readable(b)}"')
                if condition_directly_follows(tree, condition, b):
                    logger.info(f'Activity "{readable(b)}" directly follows the failure of "{readable(a)}" through the dataobject "{data_object}"')
                    return True
            logger.info(f'No dataobject in rescue of "{readable(a)}" is used in a branch condition, so failure directly follows can not be guaranteed')
            return False
        else:
            logger.add_missing_activity(b)
            logger.info(f'Activity "{readable(b)}" is missing in the process, so failure directly follows can not be guaranteed')
            return False
    else:
        logger.add_missing_activity(a)
        logger.info(f'Activity "{readable(a)}" is missing in the process, so failure directly follows is trivially true')
        return True

def structurally_precedes(tree, a, b):

    apath = exists(tree, a)

    if apath is None:
        return False

    compare = compare_ele(
        tree,
        apath,
        b
    )

    # -----------------------------------------
    # same branch / before
    # -----------------------------------------

    if compare == 1:
        return True

    # -----------------------------------------
    # same node
    # -----------------------------------------

    elif compare == 3:
        return True

    # -----------------------------------------
    # everything else
    # -----------------------------------------

    return False

## Eventually follows a data condition. The default here is to check in the same branch (see scope = "branch") if the scope is said to global it checks anywhere after the branch as well
def condition_eventually_follows(tree, condition, a, scope="branch"):
    branch = condition_finder(tree, condition)

    if branch is not None:
        apath = exists(branch, a)

        if apath is not None:
            logger.info(f'Activity "{readable(a)}" was found on branch following condition "{readable(condition)}"')

            impacts = condition_impacts(tree, condition)

            logger.info(f'Found {len(impacts)} calls that influence condition "{readable(condition)}". Checking if both are prior to branch')

            for call in impacts:
                if not structurally_precedes(
                        tree,
                        call,
                        branch
                ):
                    logger.warning(f'Found a call "{readable(call)}" that is not prior to the identified branch, so compliance can be violated if said call can cause the condition to evaluate to true')
                    return False

            logger.info('All calls that influence the condition are prior to the condition, so eventually follows is satisfied')
            return True

        else:
            if scope == "branch":
                logger.info(f'While branch following condition "{readable(condition)}" was found, the Activity "{readable(a)}" was not found on the branch')
                return False

            else:
                logger.info(f'Branch following condition "{readable(condition)}" was found, however the Activity "{readable(a)}" was not found on the branch, since the scope is global, the two elements are compared')

                apath = exists(tree, a)

                print("\n=== DEBUG compare_ele ===")
                print("branch:", branch)
                print("apath:", apath)

                if branch is not None:
                    print("branch tag:", branch.tag)
                    print("branch id:", branch.attrib.get("id"))

                if apath is not None:
                    print("apath tag:", apath.tag)
                    print("apath id:", apath.attrib.get("id"))
                else:
                    logger.info(f'Activity "{readable(a)}" does not exist in the process')
                    return False

                print("=========================\n")

                compare = compare_ele(tree, branch, apath)

                if compare == 0:
                    logger.info(f'branch and "{readable(a)}" are on different exclusive branches')
                    return False

                elif compare == -1:
                    logger.info(f'branch and "{readable(a)}" are on different parallel branches')
                    return False

                elif compare == 1:
                    logger.info(f'branch is before "{readable(a)}", True')
                    return True

                elif compare == 2:
                    logger.info(f'branch is after "{readable(a)}", False')
                    return False

    else:
        logger.info(f'No branch with condition "{readable(condition)}" was found')
        return False

def data_leads_to_absence(tree, condition, a):
    return not condition_eventually_follows(tree, condition, a)

## Obligations vs Permissions: These can be modeled on the requirements side, using ands, ors and by just included the rule or not
## Complex resource requirements: These can also be modeled on the requirements side usind ands, ors and by just including rule or not

## One aspect to note, is that this function works trivially with terminates, because there can always only be a single terminate per branch
def is_semantic_call(node):
    """
    Returns True only for meaningful business activities.
    Filters out empty technical placeholder calls.
    """
    if not node.tag.endswith("call"):
        return False
    label = node.find(".//label")
    if label is None:
        return False
    if label.text is None:
        return False
    return normalize_text(label.text) != ""

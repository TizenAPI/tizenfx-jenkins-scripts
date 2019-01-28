#!/usr/bin/env python3
#
# Copyright (c) 2019 Samsung Electronics Co., Ltd All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the License);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an AS IS BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import boto3
from boto3.dynamodb.conditions import Key, Attr


class APIComparisonResult:
    def __init__(self):
        self.old_api = dict()
        self.new_api = dict()
        self.added = set()
        self.removed = set()
        self.changed = set()
        self.total_changed_count = 0
        self.hidden_changed_count = 0

    @property
    def public_api_changed(self):
        return self.total_changed_count > self.hidden_changed_count

    @property
    def internal_api_changed(self):
        return self.hidden_changed_count > 0


class APIDB:
    def __init__(self, env):
        db = boto3.resource('dynamodb', region_name='ap-northeast-2')
        self._table = db.Table('TizenFX_API_Members')

    def compare(self, category, jsonfile):
        with open(jsonfile) as newset_file:
            newset_json = json.load(newset_file)

        kce = Key('Category').eq(category)

        response = self._table.query(
            IndexName='Category-DocId-index',
            KeyConditionExpression=kce
        )
        oldset_json = response['Items']
        while 'LastEvaluatedKey' in response:
            response = self._table.query(
                IndexName='Category-DocId-index',
                KeyConditionExpression=kce,
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            oldset_json.extend(response['Items'])

        return self._compare_json(oldset_json, newset_json)

    def put_items(self, category, item_dict):
        for docId in item_dict:
            print('[PUT] ' + docId)
            self._table.put_item(
                Item={
                    'DocId': docId,
                    'Category': category,
                    'Info': item_dict[docId]
                }
            )

    def delete_items(self, category, keys):
        for docId in keys:
            print('[DELETE] ' + docId)
            self._table.delete_item(
                Key={
                    'DocId': docId,
                    'Category': category
                }
            )

    def import_datafile(self, category, jsonfile):
        ret = self.compare(category, jsonfile)
        added_dict = {docId: ret.new_api[docId] for docId in ret.added}
        changed_dict = {docId: ret.new_api[docId] for docId in ret.changed}
        self.put_items(category, added_dict)
        self.put_items(category, changed_dict)
        self.delete_items(category, ret.removed)

    def _compare_json(self, old_json, new_json):
        ret = APIComparisonResult()

        for i in old_json:
            ret.old_api[i['DocId']] = i['Info']
        for i in new_json:
            ret.new_api[i['DocId']] = i['Info']

        inter_set = set(ret.old_api.keys()).intersection(ret.new_api.keys())
        ret.added = set(ret.new_api.keys()).difference(inter_set)
        ret.removed = set(ret.old_api.keys()).difference(inter_set)

        for i in inter_set:
            oldinfo = json.dumps(ret.old_api[i], sort_keys=True)
            newinfo = json.dumps(ret.new_api[i], sort_keys=True)
            if oldinfo != newinfo:
                ret.changed.add(i)

        ret.total_changed_count += len(ret.added) + \
            len(ret.removed) + len(ret.changed)

        for i in ret.added:
            if ret.new_api[i]['IsHidden']:
                ret.hidden_changed_count += 1
        for i in ret.removed:
            if ret.old_api[i]['IsHidden']:
                ret.hidden_changed_count += 1
        for i in ret.changed:
            if ret.new_api[i]['IsHidden'] and ret.old_api[i]['IsHidden']:
                ret.hidden_changed_count += 1

        return ret

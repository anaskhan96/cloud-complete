from bottle import request, route, run, template, get, post, delete, HTTPResponse
import json

categories = {}
users = set()
acts = []
actIds = set()

@get('/api/v1/categories')
def get_categories():
    if not categories:
        return HTTPResponse('{}', 204)
    else:
        return json.dumps(categories)

@post('/api/v1/categories')
def add_category():
    new_category = request.json[0]
    #print(new_category)

    if new_category in categories:
        return HTTPResponse('{}', 400)
    else:
        categories[new_category] = 0
        return HTTPResponse('{}', 201)

@delete('/api/v1/categories/<category>')
def delete_category(category):
    if not category in categories:
        return HTTPResponse('{}', 400)
    else:
        del categories[category]
        return HTTPResponse('{}', 200)

@get('/api/v1/categories/<category>/acts')
def get_acts(category):
    #print(acts)
    start = int(request.query.get('start', 0))
    end = int(request.query.get('end', len(acts) - 1))

    if start != 0:
        start -= 1
        end -= 1

    if not category in categories or \
        end > len(acts) or \
        (end - start + 1) > len(acts):
        return HTTPResponse('{}', 400)
    else:
        if not acts:
            return HTTPResponse('[]', 204)
        elif (end - start + 1) >= 100:
            return HTTPResponse('[]', 413)
        else:
            return json.dumps(acts[start:end+1])

@get('/api/v1/categories/<category>/acts/size')
def get_acts_size(category):
    if not category in categories:
        return HTTPResponse('{}', 400)
    else:
        resp = [len(acts)]
        return HTTPResponse(json.dumps(resp), 200)

@post('/api/v1/users')
def add_user():
    new_user = request.json
    #print(new_user)

    if new_user['username'] in users or len(new_user['password']) != 40:
        return HTTPResponse('{}', 400)
    else:
        users.add(new_user['username'])
        return HTTPResponse('{}', 201)

@delete('/api/v1/users/<username>')
def delete_user(username):
    if not username in users:
        return HTTPResponse('{}', 400)
    else:
        users.remove(username)
        return HTTPResponse('{}', 200)

@post('/api/v1/acts')
def add_act():
    new_act = request.json
    #print(new_act)

    if new_act['actId'] in actIds or \
        not new_act['username'] in users or \
        len(new_act['timestamp']) != 19 or \
        not new_act['categoryName'] in categories or \
        '$' in new_act['imgB64'] or \
        'upvotes' in new_act:
        return HTTPResponse('{}', 400) 
    else:
        new_act['upvotes'] = 0
        acts.insert(0, new_act)
        categories[new_act['categoryName']]+=1
        #print(actIds)
        actIds.add(new_act['actId'])
        #print(actIds)
        return HTTPResponse('{}', 201)

@post('/api/v1/acts/upvote')
def upvote_act():
    actId = request.json[0]
    #print(actId)
    #print(str(actId in actIds))

    if not actId in actIds:
        return HTTPResponse('{}', 400) 
    else:
        for act in acts:
            if act['actId'] == actId:
                act['upvotes']+=1
        return HTTPResponse('{}', 200)

@delete('/api/v1/acts/upvote')
def upvote_act():
    return HTTPResponse('{}', 405)

@delete('/api/v1/acts/<actId>')
def delete_act(actId):
    actId=int(actId)
    #print(actId)
    #print(actIds)
    #print(str(actId in actIds))

    if not actId in actIds:
        return HTTPResponse('{}', 400) 
    else:
        for act in acts:
            if act['actId'] == actId:
                categories[act['categoryName']]-=1
                acts.remove(act)
                actIds.remove(actId)
                break
        return HTTPResponse('{}', 200)

run(host='localhost', port=8888)
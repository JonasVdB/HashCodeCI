import requests
import json
import configparser

import shutil
import datetime
import os
import argparse
import polling




config = configparser.ConfigParser()
config.read('settings.cfg')
TOKEN = config.get('authentication','token')
round_id = config.get('authentication','round_id')

SOURCE_DIR = config.get('project','source_dir')

dataset_ids = [config.get('datasets','dataset'+str(i)) for i in range(4)]
solutions = [config.get('project','solutions'+str(i)) for i in range(4)]

topscore_dir = "topscores"


def check_submission(token,round_id, submitted):
    print('.', sep=' ', end='', flush=True)
    url = "https://hashcode-judge.appspot.com/api/judge/v1/submissions/"+round_id
    headers = {
        'authorization': "Bearer " + token,
        'content-type': "application/json;charset=utf-8",
    }
    try:
        init_res = requests.get(url, headers=headers, allow_redirects=False)
        if init_res.status_code == 200:
            items = init_res.json()['items']
            current = [t for t in items if t["id"] == submitted]
            if len(current) != 0:
                return {'scored':current[0]["scored"],'valid':current[0]["valid"],'best':current[0]["best"],'score':current[0]["score"]}
            print("Could not retrieve result")
            return None

        else:
            print("URL has not been created, your token might be expired.")
            return None
    except Exception as ce:
        print("ERROR: " + str(ce))


def zipdir(path, outputfilename):
    try:
        shutil.make_archive(outputfilename, 'zip', path)
        return True
    except Exception as ce:
        return False


def createUrl(token):
    url = "https://hashcode-judge.appspot.com/api/judge/v1/upload/createUrl"
    headers = {
        'authorization': "Bearer " + token,
        'content-type': "application/json;charset=utf-8",
    }

    try:
        init_res = requests.get(url, headers=headers, allow_redirects=False)
        if init_res.status_code == 200:
            return init_res.json()['value']
        else:
            print("URL has not been created, your token might be expired.")
            return None
    except Exception as ce:
        print("ERROR: " + str(ce))

def upload(url,filename):
    try:
        with open(filename, 'rb') as file:
            response = requests.post(url, files={filename:file})
            if response.status_code == 200:
                return response.json()[filename]
            else:
                print("Something went wrong while uploading a file")
    except Exception as ce:
        print(ce)

def submit(sourcesBlobKey,submissionBlobKey, token ,dataSet):
    url = "https://hashcode-judge.appspot.com/api/judge/v1/submissions"
    data={"dataSet":dataSet,"submissionBlobKey":submissionBlobKey,"sourcesBlobKey":sourcesBlobKey}
    headers = {
        'authorization': "Bearer " + token,
        'content-type': "application/json;charset=utf-8",
    }
    try:
        response = requests.post(url,headers=headers,params=data)
        if response.status_code == 200:
            return response.json()
        else:
            print("Something went wrong while submitting")
            print(response.json())
    except Exception as ce:
        print(ce)

def uploadFile(filename):
    uploadURL = createUrl(TOKEN)
    if uploadURL is not None:
        blobKey = upload(uploadURL,filename)
        return blobKey
    else:
        print(str(filename) + " has not been uploaded.")
        return None

def poll_submission(TOKEN,round_id,submitted):
    print('Awaiting results', sep=' ', end='', flush=True)
    try:
        polling.poll(
            lambda: check_submission(TOKEN, round_id, submitted).get("scored") == True,
            step=5,
            timeout=30
            )
        return check_submission(TOKEN, round_id, submitted)
    except polling.TimeoutException as e:
        print("\nTimed out...")
        return None


if __name__ == '__main__':
    if not os.path.exists(topscore_dir):
        os.mkdir(topscore_dir)

    source_zipfile = 'source_'+str(datetime.datetime.now().isoformat())
    zipped = zipdir(SOURCE_DIR, source_zipfile )
    parser = argparse.ArgumentParser(description='Submit a solution')
    parser.add_argument('dataset_id', metavar='ID', type=int, nargs=1,
                   help='the ID of the dataset')
    args = parser.parse_args()

    solution_id = args.dataset_id[0]
    if zipped:
        sources=uploadFile(source_zipfile+".zip")
        solution=uploadFile(solutions[solution_id])

        if sources is not None and solution is not None:
            submitted = submit(sources,solution,TOKEN,dataset_ids[solution_id])['id']
            score = poll_submission(TOKEN,round_id,submitted)
            if score is not None:
                print("\n=== SUBMISSION REPORT FOR DATASET "+str(solution_id) + " ===")
                if score.get("best"):
                    print("You have increased your top score!!")
                    shutil.move(source_zipfile+".zip", topscore_dir + "/"+str(solution_id)+"-[" + score.get("score") + "].zip") # MOVE TO TOPSCORES
                if not score.get("valid"):
                    print("The submitted solution was declared invalid.")
                    os.remove(source_zipfile+".zip") # cleanup
                else:
                    print("Score: " +  score.get("score"))
        else:
            print("Files have not been submitted.")
            os.remove(source_zipfile+".zip") # cleanup

    else:
        print("Something went wrong when zipping the source directory, exiting now...")

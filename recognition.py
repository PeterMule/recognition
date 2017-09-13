from instance.config import SQLALCHEMY_DATABASE_URI
#SQLALCHEMY_DATABASE_URI = '''mysql+pymysql://root:101Corrunpt10n@127.0.0.1/dreamteam'''
import pymysql as msq
import re
import face_recognition as fr
from os import path
import pickle as pkl
from math import log

details = SQLALCHEMY_DATABASE_URI.split(':')
details[1] = details[1][2:]
save = details[2]
details[2]=save.split('@')[0]
save = save.split('@')[1].split('/')
details.append(save[0])
details.append(save[1])
details.pop(0)



def new_student(reg_num,wrkng_dir = '' ):
    cnt = msq.connect(host=details[2],user=details[0],password=details[1],database=details[3])
    cur = cnt.cursor()
    cur.execute('SELECT ph.address FROM photos as ph  WHERE ph.reg_num = {} and ph.learning = 1'.format(reg_num))
    addresses = cur.fetchall()
    if len(addresses) < 1 :
        ValueError("The Student does not have any photos")

    allencodings = []

    for image in addresses:
        img = fr.load_image_file(os.path.join(wrkng_dir,image[0]))
        if img:
            face = fr.face_encodings(img)
            if len(face) < 1:
                ValueError("The image at |{}| did not contain a face".format(os.path.join(wrkng_dir,image)))
            elif len(face) > 1:
                ValueError("The image at |{}| contained more than one face".format(os.path.join(wrkng_dir,image)))
            allencodings.append(face[0])
        else:
            ValueError("The image at |{}| was unable to load".format(os.path.join(wrkng_dir,image)))
        
    alist = pkl.dumps(allencodings)
    cur.execute("INSERT INTO faces VALUES ((SELECT id FROM students where reg_num = %s),%s)",(reg_num,alist))
    cnt.commit()
    cur.close()
    cnt.close()

def sumlist(ls = []):
    ret = 0.0
    for i in ls:
        if i:
            ret=ret+1
    return ret

def verify_attendance(attendance_id,wrkng_dir = '',tolerance = [0.4,0.5,0.6]):
    cnt = msq.connect(host=details[2],user=details[0],password=details[1],database=details[3])
    cur = cnt.cursor()
    cur.execute('SELECT at.uploaded_photo,at.student FROM attendance as at JOIN classesas cl on cl.id = at.class_ WHERE id = {0} and cl.archived = 0'.format(attendance_id))
    result = cr.fetchone()
    if len(result) < 1:
        RuntimeError('The attendace id does not exist or the class has been archived')
    unverified_photo = os.path.join(wrkng_dir,result[0])
    img = fr.load_image_file(unverified_photo)
    if img:
        face = fr.face_encodings(img)
        if len(face) < 1:
            ValueError("The image at |{}| did not contain a face".format(unverified_photo))
        elif len(face) > 1:
            ValueError("The image at |{}| contained more than one face".format(unverified_photo))
        unverified_photo = face[0]
    else:
        ValueError("The image at |{}| was unable to load".format(unverified_photo))

    cur.execute('SELECT fc from faces where id = "{}"'.format(result[1]))
    
    dump = cur.fetchone()
    cur.close()
    cnt.close()
    if len(dump) < 1:
        new_student(result[1],wrkng_dir)

    stored_encs = pkl.loads(dump[0])

    retu = 0.0
    maxi = 0.0
    for i in tolerance:
        if i < 0 or i > 1:
            pass
        else:
            ls = fr.compare_faces(stored_encs,unverified_photo,i)
            retu += sumlist(ls) * abs(log(i))
            maxi += len(ls) * abs(log(i))

    return retu/maxi

def change_photos(reg_num,wrkng_dir = '' ):
    cnt = msq.connect(host=details[2],user=details[0],password=details[1],database=details[3])
    cur = cnt.cursor()
    cur.execute('SELECT ph.address FROM photos as ph  WHERE ph.reg_num = {} and ph.learning = 1'.format(reg_num))
    addresses = cur.fetchall()
    #throw error
    if len(addresses) < 1 :
        ValueError("The Student does not have any photos")

    allencodings = []

    for image in addresses:
        img = fr.load_image_file(os.path.join(wrkng_dir,image[0]))
        if img:
            face = fr.face_encodings(img)
            if len(face) < 1:
                ValueError("The image at |{}| did not contain a face".format(os.path.join(wrkng_dir,image)))
            elif len(face) > 1:
                ValueError("The image at |{}| contained more than one face".format(os.path.join(wrkng_dir,image)))
            allencodings.append(face[0])
        else:
            ValueError("The image at |{}| was unable to load".format(os.path.join(wrkng_dir,image)))
        
    alist = pkl.dumps(allencodings)
    cur.execute("DELETE FROM faces WHERE id = %s",(reg_num,))
    cur.execute("INSERT INTO faces VALUES ((SELECT id FROM students where reg_num = %s),%s)",(reg_num,alist))
    cnt.commit()
    cur.close()
    cnt.close()

"""
The table used is as below
CREATE TABLE `dreamteam`.`faces` (
    ->   `id` INT NOT NULL,
    ->   `fc` BLOB NULL,
    ->   PRIMARY KEY (`id`),
    ->   UNIQUE INDEX `id_UNIQUE` (`id` ASC),
    ->   CONSTRAINT `student_related`
    ->     FOREIGN KEY (`id`)
    ->     REFERENCES `dreamteam`.`students` (`id`)
    ->     ON DELETE CASCADE
    ->     ON UPDATE CASCADE)
    -> COMMENT = 'Stores the face encodings as a list pickled into a string';


    Notice the extra table is an necessary since its a one to one relationship but inclusion into the students table requires changing the sqlalchemy code as well
    I decided not to use the file as a database in preparation on the expected groth rate and also due to the errors that my occure when multiple requests are placed to alter the file at one time as well as save on cpu time
    the verification function return value is a float between 0 and one that favours verification at low tolerance

"""

from flask_restful import Api , Resource
from models import db , User as user_model

api=Api(prefix="/api")


user={
    "username":"Pooja ",
    "email":"bhardwajpooja145@gmail.com"
}




class User(Resource):   
    # @auth_required("token")
    def get(self,id=None):
        return user;

api.add_resource(User,"/users/<int:id>")
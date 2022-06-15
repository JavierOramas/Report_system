class ProcedureCode:

    def add_procedure_code(db, code, name):
        code ={
            "code": code,
            "name": name
        }

        db.ProcedureCode.insert_one(code)
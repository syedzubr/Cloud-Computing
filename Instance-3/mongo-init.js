db.createUser(
        {
            user: "admin",
            pwd: "password",
            roles: [
                {
                    role: "readWrite",
                    db: "mymongodb"
                }
            ]
        }
);

db.copyDatabase("mymongodb","mymongodb","mongodb_mst","admin","password");



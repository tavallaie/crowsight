// my_project/scripts/deploy.ts
// @ts-nocheck
import { execSync } from "child_process";

import * as fs from "fs";


function deploy() {
    console.log("Deploying application...");
    execSync("scp -r ../frontend/dist/* user@server:/var/www/html/", { stdio: "inherit" });
    console.log("Frontend deployed.");
}

deploy();

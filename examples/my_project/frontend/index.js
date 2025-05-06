// my_project/frontend/index.js
import React from "react";
import ReactDOM from "react-dom";
import Button from "./components/Button";

function App() {
    return (
        <div>
            <h1>Welcome to CrowSight Demo</h1>
            <Button label="Click Me" onClick={() => alert("Button clicked!")} />
        </div>
    );
}

ReactDOM.render(<App />, document.getElementById("root"));

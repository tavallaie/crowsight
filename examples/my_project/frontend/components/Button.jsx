// my_project/frontend/components/Button.jsx
import React from "react";
import PropTypes from "prop-types";

export default function Button({ label, onClick }) {
    return (
        <button style={{ padding: "8px 16px", borderRadius: "4px" }} onClick={onClick}>
            {label}
        </button>
    );
}

Button.propTypes = {
    label: PropTypes.string.isRequired,
    onClick: PropTypes.func,
};

Button.defaultProps = {
    onClick: () => { },
};

import React from "react";
import styles from "./Toolbar.module.css";

const Toolbar = ({ onSelectNodes, onRemoveNodes, selectMode, eraseMode }) => {
  return (
    <div className={`${styles.toolbar} no-select`}>
      <button
        className={styles.toolbarButton}
        onClick={onSelectNodes}
        style={{ backgroundColor: selectMode ? "#0056b3" : "#007bff" }}
      >
        Select Nodes
      </button>
      <button
        className={styles.toolbarButton}
        onClick={onRemoveNodes}
        style={{ backgroundColor: eraseMode ? "#0056b3" : "#007bff" }}
      >
        Remove Nodes
      </button>
    </div>
  );
};

export default Toolbar;

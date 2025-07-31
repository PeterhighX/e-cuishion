import React from "react";
import styles from "./colorbar.module.css";

const ColorBar = () => {
  // Create a horizontal gradient from the hue range you are using in your heatmap
  const gradient = `linear-gradient(to right, 
    hsl(240, 100%, 50%), 
    hsl(180, 100%, 50%), 
    hsl(120, 100%, 50%), 
    hsl(60, 100%, 50%), 
    hsl(0, 100%, 50%))`;

  return (
    <div className={styles.colorBarContainer}>
      <div className={styles.gradient} style={{ background: gradient }} />
      <div className={styles.tickContainer}>
        {[0, 1024, 2048, 3072, 4096].map((value, index) => (
          <div
            key={index}
            className="noselect"
            style={{ textAlign: "center", position: "relative" }}
          >
            <div
              style={{
                height: "8px",
                borderLeft: "1px solid black",
                position: "absolute",
                left: "50%",
                transform: "translateX(-50%)",
              }}
            />
            <span
              style={{
                position: "absolute",
                top: "5px",
                left: "50%",
                transform: "translateX(-50%)",
                fontSize: "medium",
              }}
            >
              {value}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ColorBar;

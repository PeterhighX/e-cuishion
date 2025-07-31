// components/InteractiveHeatmap.js
import React, { useState, useRef, useEffect } from "react";
import styles from "./InteractiveHeatmap.module.css";
import { ResizableBox } from "react-resizable";
import Colorbar from "./colorbar";
import "react-resizable/css/styles.css";

const InteractiveHeatmap = ({
  data,
  sensorDivRef,
  pitch,
  outlineImage = null,
  selectMode,
  eraseMode,
  setSelectMode,
}) => {
  const [dragging, setDragging] = useState(false);
  const [draggedNodes, setDraggedNodes] = useState(null);
  const [erasedNodes, setErasedNodes] = useState([]);
  const [dragCoords, setDragCoords] = useState(null);
  const [positions, setPositions] = useState({});
  const [bboxStart, setBboxStart] = useState(null);
  const [bboxEnd, setBboxEnd] = useState(null);
  const [templateDimensions, setTemplateDimensions] = useState({
    width: 0,
    height: 0,
  });
  const [templateOffset, setTemplateOffset] = useState({ top: 0, left: 0 });
  const onResize = (event, { size }) => {
    let deltaX = size.width - templateDimensions.width; //If greater than 0, x length grew, meaning we moved closer towards origin
    let deltaY = size.height - templateDimensions.height; //If greater than 0, y length grew, meaning we moved closer towards origin
    setTemplateDimensions(size);
    setTemplateOffset({
      top: templateOffset.top - deltaY,
      left: templateOffset.left - deltaX,
    });
  };
  const containerRef = useRef(null);

  const marginNodes = 2; //Number of nodes to leave for "dragging room" on top and bottom of heatmap
  const numRows = data.length;
  const numCols = data[0].length;

  const [cellSize, setCellSize] = useState(0);
  const scaleFactor = outlineImage ? 2 : 1;

  useEffect(() => {
    if (sensorDivRef.current) {
      const { clientWidth, clientHeight } = sensorDivRef.current;
      const estNodeWidth =
        clientWidth / scaleFactor / (numCols + 2 * marginNodes);
      const estNodeHeight = (clientHeight - 40) / (numRows + 2 * marginNodes);
      const thiscellSize = Math.min(estNodeHeight, estNodeWidth);
      setCellSize(thiscellSize - pitch);
      setTemplateDimensions({
        width: thiscellSize * numCols,
        height: thiscellSize * numRows,
      });
      setTemplateOffset({
        top: (clientHeight - thiscellSize * numRows) / 2,
        left: clientWidth / 2,
      });
    }
  }, [sensorDivRef.current]);

  useEffect(() => {
    const initialPositions = {};
    const { clientWidth, clientHeight } = sensorDivRef.current;
    data.forEach((row, rowIndex) => {
      row.forEach((_, colIndex) => {
        initialPositions[`${rowIndex}-${colIndex}`] = {
          x:
            colIndex * (cellSize + pitch) +
            (clientWidth / scaleFactor - (cellSize + pitch) * numCols) / 2,
          y:
            rowIndex * (cellSize + pitch) +
            (clientHeight - (cellSize + pitch) * numRows) / 2,
        };
      });
    });
    setPositions(initialPositions);
  }, [cellSize]);

  const handleMouseDownCell = (row, col, event) => {
    if (eraseMode) {
      setErasedNodes((prevErased) => {
        return [...prevErased, `${row}-${col}`];
      });
    } else if (!selectMode) {
      setDragging(true);
      const { clientX, clientY } = event;
      const rect = containerRef.current.getBoundingClientRect();
      const x = clientX - rect.left;
      const y = clientY - rect.top;
      setDragCoords({ x, y });
      if (!draggedNodes) {
        setDraggedNodes([`${row}-${col}`]);
      }
    }
  };

  const handleMouseDownHeatmap = (event) => {
    if (selectMode) {
      const rect = containerRef.current.getBoundingClientRect();
      setDragging(true);
      setBboxStart({
        x: event.clientX - rect.left,
        y: event.clientY - rect.top,
      });
      setBboxEnd({
        x: event.clientX - rect.left,
        y: event.clientY - rect.top,
      });
    }
  };

  function getEncapsulatedNodes() {
    let boxLeft = Math.min(bboxStart.x, bboxEnd.x);
    let boxTop = Math.min(bboxStart.y, bboxEnd.y);
    let boxRight = Math.max(bboxStart.x, bboxEnd.x);
    let boxBottom = Math.max(bboxStart.y, bboxEnd.y);
    const encapsulatedNodes = [];

    Object.entries(positions).forEach(([nodeId, { x, y }]) => {
      const nodeLeft = x;
      const nodeRight = x + cellSize;
      const nodeTop = y;
      const nodeBottom = y + cellSize;

      // Check if the node is at least partially within the bounding box
      const isEncapsulated =
        nodeRight >= boxLeft &&
        nodeLeft <= boxRight &&
        nodeBottom >= boxTop &&
        nodeTop <= boxBottom;

      if (isEncapsulated) {
        encapsulatedNodes.push(nodeId);
      }
    });

    return encapsulatedNodes;
  }

  const handleMouseUp = () => {
    setDragging(false);
    if (selectMode) {
      if (eraseMode) {
        setErasedNodes((prevErased) => {
          let newNodes = getEncapsulatedNodes();
          return [...prevErased, ...newNodes];
        });
      } else {
        setDraggedNodes(getEncapsulatedNodes());
      }
      setSelectMode(false);
    } else {
      setDraggedNodes(null);
    }
    setBboxEnd({});
    setBboxStart({});
    setDragCoords(null);
  };

  const handleMouseLeave = () => {
    setDragging(false);
    if (selectMode) {
      if (eraseMode) {
        setErasedNodes((prevErased) => {
          let newNodes = getEncapsulatedNodes();
          return [...prevErased, ...newNodes];
        });
      } else {
        setDraggedNodes(getEncapsulatedNodes());
      }
      setSelectMode(false);
    } else {
      setDraggedNodes(null);
    }
    setBboxEnd({});
    setBboxStart({});
    setDragCoords(null);
  };

  const handleMouseMove = (event) => {
    if (dragging && draggedNodes && !selectMode) {
      const { clientX, clientY } = event;
      const rect = containerRef.current.getBoundingClientRect();
      const x = clientX - rect.left;
      const y = clientY - rect.top;
      const deltaX = x - dragCoords.x;
      const deltaY = y - dragCoords.y;
      const updatedPositions = { ...positions };
      draggedNodes.forEach((nodeId) => {
        updatedPositions[nodeId].x += deltaX;
        updatedPositions[nodeId].y += deltaY;
      });
      setPositions(updatedPositions);
      setDragCoords({ x, y });
    } else if (dragging && selectMode) {
      const rect = containerRef.current.getBoundingClientRect();
      setBboxEnd({ x: event.clientX - rect.left, y: event.clientY - rect.top });
    }
  };

  const getColor = (value) => {
    const hue = (1 - value / 4096) * 240;
    return `hsl(${hue}, 100%, 50%)`;
  };

  const handleDragStart = (e) => {
    e.preventDefault();
  };

  const handleDrop = (e) => {
    e.preventDefault();
  };

  const getBoundingBoxStyle = () => {
    const left = Math.min(bboxStart.x, bboxEnd.x);
    const top = Math.min(bboxStart.y, bboxEnd.y);
    const width = Math.abs(bboxStart.x - bboxEnd.x);
    const height = Math.abs(bboxStart.y - bboxEnd.y);

    return {
      position: "absolute",
      left,
      top,
      width,
      height,
      border: "2px dashed blue",
      pointerEvents: "none",
      zIndex: 5,
    };
  };

  return (
    <div
      className={`${styles.heatmap} ${styles.noselect}`}
      ref={containerRef}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseDown={handleMouseDownHeatmap}
      handleDragStart={handleDragStart}
      handleDrop={handleDrop}
      onMouseLeave={handleMouseLeave}
    >
      {selectMode && bboxStart && <div style={getBoundingBoxStyle()} />}
      <Colorbar></Colorbar>
      {data.map((row, rowIndex) => (
        <div key={rowIndex} className={styles.row}>
          {row.map((value, colIndex) => {
            const position = positions[`${rowIndex}-${colIndex}`];
            const nodeId = `${rowIndex}-${colIndex}`;
            return (
              <div
                key={colIndex}
                className={`${styles.cell}`}
                style={{
                  backgroundColor:
                    draggedNodes && draggedNodes.includes(nodeId)
                      ? "aquamarine"
                      : getColor(value),
                  position: "absolute",
                  left: position ? position.x : colIndex * cellSize,
                  top: position ? position.y : rowIndex * cellSize,
                  zIndex:
                    draggedNodes && draggedNodes.includes(nodeId) ? 1000 : 2,
                  cursor: dragging ? "grabbing" : "grab",
                  width: cellSize,
                  height: cellSize,
                  display:
                    erasedNodes && erasedNodes.includes(nodeId)
                      ? "none"
                      : "block",
                }}
                onMouseDown={(e) => handleMouseDownCell(rowIndex, colIndex, e)}
                onMouseEnter={(e) => {
                  e.target.style.border = "1px solid black";
                }}
                onMouseLeave={(e) => {
                  e.target.style.border = "none";
                }}
                handleDragStart={handleDragStart}
                handleDrop={handleDrop}
              />
            );
          })}
        </div>
      ))}
      {outlineImage && (
        <ResizableBox
          handleDragStart={handleDragStart}
          handleDrop={handleDrop}
          style={{
            position: "absolute",
            top: templateOffset.top,
            left: templateOffset.left,
            zIndex: 1,
            userSelect: "none",
            // width: "50%",
            // height: (cellSize + pitch) * numRows,
          }}
          width={templateDimensions.width}
          height={templateDimensions.height}
          onResize={onResize}
          resizeHandles={["nw"]}
        >
          <img
            className={styles.noselect}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "contain",
              position: "absolute",
              zIndex: -1,
            }}
            src={`/${outlineImage}`}
          ></img>
        </ResizableBox>
      )}
    </div>
  );
};

export default InteractiveHeatmap;

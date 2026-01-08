import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import * as pdfjsLib from 'pdfjs-dist/build/pdf';
import { Stage, Layer, Image, Rect, Text } from 'react-konva';
import './style.css';

pdfjsLib.GlobalWorkerOptions.workerSrc = `/pdf.worker.min.mjs`;

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const FileUpload = ({ onUpload, loading }) => (
    <div className="upload-container">
        <header>
            <h1>Invoice Extraction Agent</h1>
            <p>Upload invoice images or PDFs to automatically extract structured data.</p>
        </header>
        <div className="upload-box">
            <input
                type="file"
                id="file-upload"
                accept="application/pdf, image/jpeg, image/png"
                onChange={onUpload}
                multiple
                style={{ display: 'none' }}
            />
            <label htmlFor="file-upload" className={`upload-label ${loading ? 'loading' : ''}`}>
                {loading ? 'Processing...' : 'Select Files'}
            </label>
        </div>
    </div>
);

const ImageViewer = ({ images, highlight, imageDimensions, scale, areasOfInterest, isProcessing }) => {
    const containerRef = useRef(null);

    useEffect(() => {
        if (highlight && highlight.bbox && containerRef.current) {
            const { y1 } = highlight.bbox;
            const scrollPos = y1 * scale - 100;
            containerRef.current.scrollTo({
                top: Math.max(0, scrollPos),
                behavior: 'smooth'
            });
        }
    }, [highlight, scale]);

    let currentY = 0;
    const imageElements = images.map((img, index) => {
        const imageElement = (
            <Image
                key={index}
                image={img}
                x={0}
                y={currentY}
                width={img.width}
                height={img.height}
            />
        );
        currentY += img.height;
        return imageElement;
    });

    return (
        <div className="image-viewer" ref={containerRef}>
            <Stage 
                width={imageDimensions.width * scale} 
                height={imageDimensions.height * scale} 
                scaleX={scale} 
                scaleY={scale}
            >
                <Layer>
                    {imageElements}
                </Layer>
                {/* Layer for Ghost Areas of Interest */}
                {areasOfInterest && (
                    <Layer opacity={0.6}>
                        {Object.entries(areasOfInterest).map(([key, bbox]) => {
                            if (!bbox) return null;
                            const colors = {
                                header_area: '#4285f4',
                                line_items_area: '#34a853',
                                summary_area: '#fbbc05'
                            };
                            return (
                                <React.Fragment key={key}>
                                    <Rect
                                        x={bbox.x1}
                                        y={bbox.y1}
                                        width={bbox.x2 - bbox.x1}
                                        height={bbox.y2 - bbox.y1}
                                        stroke={colors[key]}
                                        strokeWidth={2 / scale}
                                        dash={[10, 5]}
                                    />
                                    <Text
                                        x={bbox.x1}
                                        y={bbox.y1 - 20 / scale}
                                        text={key.replace(/_/g, ' ').toUpperCase()}
                                        fontSize={14 / scale}
                                        fill={colors[key]}
                                        fontStyle="bold"
                                    />
                                </React.Fragment>
                            );
                        })}
                    </Layer>
                )}
                <Layer>
                    {highlight && highlight.bbox && (
                        <Rect
                            x={highlight.bbox.x1}
                            y={highlight.bbox.y1}
                            width={highlight.bbox.x2 - highlight.bbox.x1}
                            height={highlight.bbox.y2 - highlight.bbox.y1}
                            fill="rgba(255, 255, 0, 0.3)"
                            stroke="#ffcc00"
                            strokeWidth={3 / scale}
                        />
                    )}
                </Layer>
            </Stage>
        </div>
    );
};

const ExtractedData = ({ data, schema, onHover, isProcessing }) => {
    const renderValue = (fieldData) => {
        if (!fieldData) return <span className="no-value">{isProcessing ? '...' : 'N/A'}</span>;
        
        const val = typeof fieldData === 'object' && fieldData !== null ? fieldData.value : fieldData;
        
        if (typeof val === 'undefined' || val === null || val === '') {
            return <span className="no-value">{isProcessing ? '...' : 'N/A'}</span>;
        }
        
        if (typeof val === 'number') {
            return val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        }
        
        return String(val);
    };

    const handleRowHover = (item) => {
        if (item && item.bbox) {
            onHover(item);
        } else {
            onHover(null);
        }
    };

    return (
        <div className="extracted-data">
            <section className="data-section">
                <h3>General Information</h3>
                <table className="data-table">
                    <tbody>
                        {Object.entries(schema.properties).map(([key, fieldSchema]) => {
                            if (key === 'line_items' || key === 'bbox') return null;
                            const fieldData = data[key];
                            return (
                                <tr 
                                    key={key} 
                                    onMouseEnter={() => handleRowHover(fieldData)} 
                                    onMouseLeave={() => onHover(null)}
                                    className={fieldData?.bbox ? 'has-highlight' : ''}
                                >
                                    <td className="field-label">{fieldSchema.title || key}</td>
                                    <td className="field-value">{renderValue(fieldData)}</td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </section>

            {((data.line_items && data.line_items.length > 0) || isProcessing) && (
                <section className="data-section">
                    <h3>Line Items</h3>
                    <div className="table-container">
                        <table className="data-table line-items-table">
                            <thead>
                                <tr>
                                    <th>Description</th>
                                    <th>Qty</th>
                                    <th>Unit Price</th>
                                    <th>Total</th>
                                </tr>
                            </thead>
                            <tbody>
                                {(data.line_items || []).map((item, index) => (
                                    <tr 
                                        key={index} 
                                        onMouseEnter={() => handleRowHover(item)} 
                                        onMouseLeave={() => onHover(null)}
                                        className={item.bbox ? 'has-highlight' : ''}
                                    >
                                        <td>{renderValue(item.description)}</td>
                                        <td>{renderValue(item.quantity)}</td>
                                        <td>{renderValue(item.unit_price)}</td>
                                        <td>{renderValue(item.total_price)}</td>
                                    </tr>
                                ))}
                                {isProcessing && (!data.line_items || data.line_items.length === 0) && (
                                    <tr>
                                        <td colSpan="4" className="loading-row">Extracting items...</td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </section>
            )}
        </div>
    );
};

const InvoiceView = ({ images, extractedData, schema, areasOfInterest, isProcessing }) => {
    const [highlight, setHighlight] = useState(null);
    const [viewerWidth, setViewerWidth] = useState(800);
    const containerRef = useRef(null);

    const imageDimensions = {
        width: images.length > 0 ? Math.max(...images.map(img => img.width)) : 0,
        height: images.length > 0 ? images.reduce((sum, img) => sum + img.height, 0) : 0,
    };

    useEffect(() => {
        if (containerRef.current) {
            const updateWidth = () => {
                const viewerElement = containerRef.current.querySelector('.image-viewer');
                if (viewerElement) {
                    setViewerWidth(viewerElement.offsetWidth - 64);
                }
            };
            updateWidth();
            const resizeObserver = new ResizeObserver(updateWidth);
            resizeObserver.observe(containerRef.current);
            return () => resizeObserver.disconnect();
        }
    }, []);

    const scale = imageDimensions.width > 0 ? viewerWidth / imageDimensions.width : 1;

    return (
        <div className="invoice-view-container" ref={containerRef}>
            <ImageViewer 
                images={images} 
                highlight={highlight} 
                imageDimensions={imageDimensions} 
                scale={scale} 
                areasOfInterest={areasOfInterest}
                isProcessing={isProcessing}
            />
            <ExtractedData 
                data={extractedData} 
                schema={schema} 
                onHover={setHighlight} 
                isProcessing={isProcessing}
            />
        </div>
    );
};




function App() {
    const [schema, setSchema] = useState(null);
    const [images, setImages] = useState([]);
    const [extractedData, setExtractedData] = useState(null);
    const [agentStatus, setAgentStatus] = useState('');
    const [progress, setProgress] = useState(0);
    const [areasOfInterest, setAreasOfInterest] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const abortControllerRef = useRef(null);

    useEffect(() => {
        const fetchSchema = async () => {
            try {
                const response = await axios.get(`${API_BASE_URL}/api/invoice-schema`);
                setSchema(response.data);
            } catch (err) {
                setError('Failed to load invoice schema.');
            }
        };
        fetchSchema();
    }, []);

    const resetState = useCallback(() => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }
        setExtractedData(null);
        setImages([]);
        setAgentStatus('');
        setProgress(0);
        setAreasOfInterest(null);
        setLoading(false);
        setError('');
    }, []);

    const handleCancel = useCallback(() => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
            setAgentStatus('Cancelled');
            setLoading(false);
        }
    }, []);

    const processFiles = useCallback(async (files) => {
        setLoading(true);
        setError('');
        setExtractedData({});
        setImages([]);
        setAgentStatus('Preparing image...');
        setProgress(5);
        setAreasOfInterest(null);
        
        abortControllerRef.current = new AbortController();

        const imagePromises = Array.from(files).map(file => {
            return new Promise((resolve, reject) => {
                if (file.type.startsWith('image/')) {
                    const reader = new FileReader();
                    reader.onload = () => {
                        const img = new window.Image();
                        img.onload = () => resolve([img]);
                        img.src = reader.result;
                    };
                    reader.readAsDataURL(file);
                } else if (file.type === 'application/pdf') {
                    const reader = new FileReader();
                    reader.onload = async () => {
                        const pdf = await pdfjsLib.getDocument({ data: reader.result }).promise;
                        const pageImages = [];
                        for (let i = 1; i <= pdf.numPages; i++) {
                            const page = await pdf.getPage(i);
                            const viewport = page.getViewport({ scale: 2.0 });
                            const canvas = document.createElement('canvas');
                            canvas.width = viewport.width;
                            canvas.height = viewport.height;
                            const context = canvas.getContext('2d');
                            await page.render({ canvasContext: context, viewport }).promise;
                            const img = new window.Image();
                            img.src = canvas.toDataURL();
                            await new Promise(r => img.onload = r);
                            pageImages.push(img);
                        }
                        resolve(pageImages);
                    };
                    reader.readAsArrayBuffer(file);
                } else {
                    resolve([]);
                }
            });
        });

        const allImages = (await Promise.all(imagePromises)).flat();
        setImages(allImages);

        if (allImages.length > 0) {
            const stitchedCanvas = document.createElement('canvas');
            const ctx = stitchedCanvas.getContext('2d');
            
            let totalHeight = 0;
            let maxWidth = 0;
            allImages.forEach(img => {
                totalHeight += img.height;
                maxWidth = Math.max(maxWidth, img.width);
            });

            stitchedCanvas.width = maxWidth;
            stitchedCanvas.height = totalHeight;

            let y = 0;
            allImages.forEach(img => {
                ctx.drawImage(img, 0, y);
                y += img.height;
            });
            
            stitchedCanvas.toBlob(async (blob) => {
                const formData = new FormData();
                formData.append('file', blob, 'invoice.jpg');
                
                try {
                    const response = await fetch(`${API_BASE_URL}/api/extract-invoice`, {
                        method: 'POST',
                        body: formData,
                        signal: abortControllerRef.current.signal
                    });

                    const reader = response.body.getReader();
                    const decoder = new TextDecoder();
                    let buffer = '';
                    
                    while (true) {
                        const { value, done } = await reader.read();
                        if (done) break;
                        
                        buffer += decoder.decode(value, { stream: true });
                        const lines = buffer.split('\n');
                        
                        // Keep the last partial line in the buffer
                        buffer = lines.pop();
                        
                        for (const line of lines) {
                            const trimmedLine = line.trim();
                            if (!trimmedLine || !trimmedLine.startsWith('data: ')) continue;
                            
                            try {
                                const data = JSON.parse(trimmedLine.substring(6));
                                
                                if (data.error) {
                                    setError(data.error);
                                    setLoading(false);
                                    return;
                                }

                                const nodeName = Object.keys(data)[0];
                                const nodeData = data[nodeName];

                                if (nodeName === 'extract_structured_ocr') {
                                    setAgentStatus('Reading text...');
                                    setProgress(20);
                                } else if (nodeName === 'decide_aoi') {
                                    setAgentStatus('Identifying layout...');
                                    setProgress(40);
                                    setAreasOfInterest(nodeData.areas_of_interest);
                                } else if (nodeName === 'extract_header_data') {
                                    setAgentStatus('Extracting header details...');
                                    setProgress(60);
                                    setExtractedData(prev => ({ ...prev, ...nodeData.extracted_header }));
                                } else if (nodeName === 'extract_line_items_data') {
                                    setAgentStatus('Parsing line items...');
                                    setProgress(80);
                                    setExtractedData(prev => ({
                                        ...prev,
                                        line_items: nodeData.extracted_line_items?.line_items || []
                                    }));
                                } else if (nodeName === 'extract_summary_data') {
                                    setAgentStatus('Calculating totals...');
                                    setProgress(90);
                                    setExtractedData(prev => ({ ...prev, ...nodeData.extracted_summary }));
                                } else if (nodeName === 'aggregate_results') {
                                    setAgentStatus('Completed');
                                    setProgress(100);
                                    setExtractedData(nodeData.extracted_data);
                                    setLoading(false);
                                }
                            } catch (parseErr) {
                                console.error('Error parsing SSE line:', parseErr, trimmedLine);
                            }
                        }
                    }
                } catch (err) {
                    if (err.name === 'AbortError') {
                        console.log('Fetch aborted');
                    } else {
                        setError('Failed to extract data: ' + err.message);
                        setLoading(false);
                    }
                }
            }, 'image/jpeg');
        } else {
            setLoading(false);
        }
    }, []);

    const handleUpload = (e) => {
        if (e.target.files.length > 0) {
            processFiles(e.target.files);
        }
    };

    if (!schema) {
        return <div className="loading-indicator">Loading schema...</div>;
    }

    const hasData = extractedData && (Object.keys(extractedData).length > 0 || loading);

    return (
        <div>
            {!hasData && !loading ? (
                <FileUpload onUpload={handleUpload} loading={loading} />
            ) : (
                <>
                    <div className="status-bar">
                        <div className="status-content">
                            <div className="status-info">
                                <span className={`status-dot ${loading ? 'pulse' : 'completed'}`}></span>
                                <span className="status-text">{agentStatus}</span>
                            </div>
                            <div className="progress-container">
                                <div 
                                    className={`progress-fill ${!loading ? 'completed' : ''}`} 
                                    style={{ width: `${progress}%` }}
                                ></div>
                            </div>
                        </div>
                        <div className="status-actions">
                            {loading ? (
                                <button className="btn btn-cancel" onClick={handleCancel}>Cancel</button>
                            ) : (
                                <button className="btn btn-primary" onClick={resetState}>Parse Another</button>
                            )}
                        </div>
                    </div>
                    <InvoiceView 
                        images={images} 
                        extractedData={extractedData} 
                        schema={schema} 
                        areasOfInterest={areasOfInterest}
                        isProcessing={loading}
                    />
                </>
            )}
            {error && <div className="error-message">{error}</div>}
        </div>
    );
}

export default App;

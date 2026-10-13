import React, { useEffect, useRef, useState } from "react";

interface AudioMeterProps {
  stream: MediaStream | null;
  isRecording: boolean;
}

export const AudioMeter: React.FC<AudioMeterProps> = ({ stream, isRecording }) => {
  const [level, setLevel] = useState<number>(0);
  const animationFrameRef = useRef<number | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);

  useEffect(() => {
    if (!stream || !isRecording) {
      setLevel(0);
      return;
    }

    try {
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const audioCtx = new AudioCtx();
      audioContextRef.current = audioCtx;

      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      const source = audioCtx.createMediaStreamSource(stream);
      source.connect(analyser);

      const dataArray = new Uint8Array(analyser.frequencyBinCount);

      const updateMeter = () => {
        analyser.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
          sum += dataArray[i];
        }
        const average = sum / dataArray.length;
        // Normalize between 0 and 100
        const normalized = Math.min(100, Math.round((average / 128) * 100));
        setLevel(normalized);

        animationFrameRef.current = requestAnimationFrame(updateMeter);
      };

      updateMeter();
    } catch {
      // AudioContext unavailable or restricted
    }

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      if (audioContextRef.current) {
        audioContextRef.current.close().catch(() => {});
      }
    };
  }, [stream, isRecording]);

  return (
    <div className="audio-meter">
      <div className="audio-meter-label">
        <span>Mic Level</span>
        <span>{level}%</span>
      </div>
      <div className="audio-meter-track">
        <div
          className={`audio-meter-bar ${
            level > 75 ? "peak" : level > 40 ? "good" : "low"
          }`}
          style={{ width: `${level}%` }}
        />
      </div>
    </div>
  );
};

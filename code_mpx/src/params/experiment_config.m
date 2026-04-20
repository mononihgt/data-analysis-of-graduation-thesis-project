function cfg = experiment_config(screenNumber, winRect)
% Unified experiment parameters.
% Optional inputs (screenNumber, winRect) enable visual-angle to pixel conversion.

    cfg.visualAngleDeg = 9.8;
    cfg.viewingDistanceCm = 50;

    cfg.squareBorderWidthPx = 4;
    cfg.matchToleranceRatio = 0.05;

    cfg.barInsetRatio = 0.08;
    cfg.barWidthRatio = 0.25;
    cfg.barStepRatio = 0.005;
    cfg.targetMinRatio = 0.125;

    cfg.circleRadiusRatio = 0.10;
    cfg.circleOffsetRatio = 0.20;
    cfg.dashLengthRatio = 0.0125;
    cfg.dashGapRatio = 0.0075;
    cfg.angleStepDeg = 3;

    cfg.defaultDisplayWidthCm = 53;
    cfg.defaultDisplayHeightCm = 30;

    cfg.squareSidePx = [];
    cfg.squareSideCm = 2 * cfg.viewingDistanceCm * tand(cfg.visualAngleDeg / 2);
    cfg.pxPerCm = [];

    if nargin < 2
        return;
    end

    [displayWidthMM, displayHeightMM] = Screen('DisplaySize', screenNumber);
    if displayWidthMM > 0 && displayHeightMM > 0
        displayWidthCm = displayWidthMM / 10;
        displayHeightCm = displayHeightMM / 10;
    else
        displayWidthCm = cfg.defaultDisplayWidthCm;
        displayHeightCm = cfg.defaultDisplayHeightCm;
    end

    pxPerCmX = winRect(3) / displayWidthCm;
    pxPerCmY = winRect(4) / displayHeightCm;
    cfg.pxPerCm = mean([pxPerCmX, pxPerCmY]);
    cfg.squareSidePx = round(cfg.squareSideCm * cfg.pxPerCm);
end

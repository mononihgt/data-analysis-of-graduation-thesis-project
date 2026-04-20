function ptb_draw_dashed_line(win, color, startPoint, endPoint, dashLength, gapLength)
    % 计算线段总长度和方向
    dx = endPoint(1) - startPoint(1);
    dy = endPoint(2) - startPoint(2);
    lineLength = sqrt(dx^2 + dy^2);

    % 单位方向向量
    if lineLength <= 0
        return;
    end
    ux = dx / lineLength;
    uy = dy / lineLength;

    % 绘制虚线
    currentPos = 0;
    while currentPos < lineLength
        dashStart = [startPoint(1) + currentPos * ux, startPoint(2) + currentPos * uy];
        nextPos = min(currentPos + dashLength, lineLength);
        dashEnd = [startPoint(1) + nextPos * ux, startPoint(2) + nextPos * uy];
        Screen('DrawLine', win, color, dashStart(1), dashStart(2), dashEnd(1), dashEnd(2), 2);
        currentPos = nextPos + gapLength;
    end
end

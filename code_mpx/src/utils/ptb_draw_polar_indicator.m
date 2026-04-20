function ptb_draw_polar_indicator(win, squareColor, centerX, centerY, radius, fixedEndX, fixedEndY, dashLength, gapLength, movableAngle)
    % 计算可移动半径的端点
    movableEndX = centerX + radius * cos(movableAngle);
    movableEndY = centerY - radius * sin(movableAngle);

    % 绘制圆和半径
    Screen('FrameOval', win, squareColor, [centerX - radius, centerY - radius, centerX + radius, centerY + radius], 2);
    ptb_draw_dashed_line(win, squareColor, [centerX, centerY], [fixedEndX, fixedEndY], dashLength, gapLength);
    Screen('DrawLine', win, squareColor, centerX, centerY, movableEndX, movableEndY, 2);
end

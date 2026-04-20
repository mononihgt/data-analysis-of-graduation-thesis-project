function ptb_draw_fixation(win, winRect, color)
    text = '+';
    [center_x, center_y] = RectCenter(winRect);
    Screen('TextSize', win, 35);
    [normBoundsRect, ~] = Screen('TextBounds', win, text);
    textWidth = normBoundsRect(3);
    textHeight = normBoundsRect(4);
    xPos = center_x - textWidth / 2;
    yPos = center_y - textHeight / 2;
    Screen('DrawText', win, text, xPos, yPos, color);
    Screen('Flip', win);
end

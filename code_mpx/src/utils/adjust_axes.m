function [Xlength,Ylength,Xrange,Yrange]=adjust_axes(win,key,Ftex,FRect,line,dot,position)

% 初始化参数
dotColor = [225 225 225];      % 白色圆点
dotSize = 10;            % 圆点直径（像素）
axesColor = [225 225 225];     % 白色坐标轴
lineWidth = 2;           % 坐标轴线宽

% 初始坐标轴长度
xAxisLength = 200;       % 横轴初始长度
yAxisLength = 200;       % 纵轴初始长度
stepSize = 10;           % 每次按键调整的步长
lastKeyCode = zeros(1, 256);

while true
    % 中央分割线
    Screen('DrawLine', win, line.Color, ...
           line.Start(1), line.Start(2), line.End(1), line.End(2), line.Width);
    
    % 右侧屏幕是面孔
    for i = 1:6
        brightness = 0.5; % 0-1范围
        Screen('Drawtexture',win,Ftex{i},[],FRect(position(i),:), 0, [], brightness);
    end

    % 绘制中心圆点
    Screen('DrawDots', win, [dot.x; dot.y], dotSize, dotColor, [], 2);

    % 绘制坐标轴
    % 横轴（水平线）
    Screen('DrawLine', win, axesColor, ...
           dot.x, dot.y, ...
           dot.x + xAxisLength, dot.y, lineWidth);
    
    % 纵轴（垂直线）
    Screen('DrawLine', win, axesColor, ...
           dot.x, dot.y, ...
           dot.x, dot.y - yAxisLength, lineWidth);

    % 刷新显示
    Screen('Flip', win);
    
    % 检测按键
    [keyIsDown, ~, keyCode] = KbCheck;
    if keyIsDown

        % 空格键确认
        if keyCode(KbName('SPACE'))
            Xlength = xAxisLength;
            Ylength = yAxisLength;
            break;
        end

        % 检测按键变化或持续按键
        keyChanged = any(keyCode ~= lastKeyCode);
                
        if keyChanged || (keyIsDown && any(keyCode([key.LeftArrow, key.RightArrow, key.UpArrow, key.DownArrow])))

            % 左右键调整横轴长度
            if keyCode(KbName('RightArrow'))
                xAxisLength = min(xAxisLength + stepSize, (line.Start(1)-3-dot.x));
            end
            if keyCode(KbName('LeftArrow'))
                xAxisLength = max(0, xAxisLength - stepSize); % 最小长度限制
            end
            
            % 上下键调整纵轴长度
            if keyCode(KbName('UpArrow'))
                yAxisLength = min(yAxisLength + stepSize, dot.y);
            end
            if keyCode(KbName('DownArrow'))
                yAxisLength = max(0, yAxisLength - stepSize); % 最小长度限制
            end

            % 如果是新按下的键，等待一小段时间后开始连续变化
            if keyChanged
                WaitSecs(0.1); % 初始延迟
            else
                WaitSecs(0.05); % 连续变化延迟
            end
        end

        % 更新上一次的按键状态
        lastKeyCode = keyCode;
    else
        % 没有按键时重置状态
        lastKeyCode = zeros(1, 256);
    end
end

%%
Screen('Flip', win);
WaitSecs(0.5);

% 矩形初始化
% 设置矩形参数
rectWidth = 100;    % 矩形宽度
rectHeight = 100;   % 矩形高度
penWidth = 3;       % 边框线宽
rectColor = [225 225 225]; % 白色边框

while true
    % 中央分割线
    Screen('DrawLine', win, line.Color, ...
           line.Start(1), line.Start(2), line.End(1), line.End(2), line.Width);
    
    % 右侧屏幕是面孔
    for i = 1:6
        brightness = 0.5; % 0-1范围
        Screen('Drawtexture',win,Ftex{i},[],FRect(position(i),:), 0, [], brightness);
    end
    
    % 绘制中心圆点
    Screen('DrawDots', win, [dot.x; dot.y], dotSize, dotColor, [], 2);
    
    % 绘制坐标轴
    % 横轴（水平线）
    Screen('DrawLine', win, axesColor, ...
           dot.x, dot.y, ...
           dot.x + xAxisLength, dot.y, lineWidth);
    
    % 纵轴（垂直线）
    Screen('DrawLine', win, axesColor, ...
           dot.x, dot.y, ...
           dot.x, dot.y - yAxisLength, lineWidth);

    % 矩形
    % 计算矩形坐标 [left, top, right, bottom]
    rect = [dot.x, dot.y - rectHeight, ...
            dot.x + rectWidth, dot.y];
    Screen('FrameRect', win, rectColor, rect, penWidth);
    Screen('Flip', win);

    % 检测按键
    [keyIsDown, ~, keyCode] = KbCheck;
    if keyIsDown
        % 空格确认
        if keyCode(KbName('SPACE'))
            Xrange = rectWidth;
            Yrange = rectHeight;
            break;
        end

        % 检测按键变化或持续按键
        keyChanged = any(keyCode ~= lastKeyCode);
                
        if keyChanged || (keyIsDown && any(keyCode([key.LeftArrow, key.RightArrow, key.UpArrow, key.DownArrow])))

            % 左右键调整横轴长度
            if keyCode(KbName('RightArrow'))
                rectWidth = min(rectWidth + stepSize, xAxisLength);
            end
            if keyCode(KbName('LeftArrow'))
                rectWidth = max(0, rectWidth - stepSize); % 最小长度限制
            end
            
            % 上下键调整纵轴长度
            if keyCode(KbName('UpArrow'))
                rectHeight = min(rectHeight + stepSize, yAxisLength);
            end
            if keyCode(KbName('DownArrow'))
                rectHeight = max(0, rectHeight - stepSize); % 最小长度限制
            end
        
            % 如果是新按下的键，等待一小段时间后开始连续变化
            if keyChanged
                WaitSecs(0.1); % 初始延迟
            else
                WaitSecs(0.05); % 连续变化延迟
            end
        end

        % 更新上一次的按键状态
        lastKeyCode = keyCode;
    else
        % 没有按键时重置状态
        lastKeyCode = zeros(1, 256);
    end

end

end
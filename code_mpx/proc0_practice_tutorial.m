% matlabfile

try
    clear all;

    %设置文件路径
    s = pwd;
    addpath(genpath(s));
    path.ori = s;
    path.intro = [s '\Stimuli\intro'];

    subinfo = getsubinfo;

%% 
    % 设置参数
    [fix,key,rgb,win,winRect,width,height,sizes,Rect_EPtask,facebar,TRect] = load_EPpara;
    [center_x,center_y] = RectCenter(winRect);
    
    % 加载提示图片
    Ttex{1} = load_image(win,path.intro,'left_match.png',path.ori);
    Ttex{2} = load_image(win,path.intro,'right_match.png',path.ori);
    Ttex{3} = load_image(win,path.intro,'all_match.png',path.ori);
    
    % 加载指导语图片
    IntroTex{1} = load_image(win,path.intro,'proc0_intro1.png',path.ori);
    IntroTex{2} = load_image(win,path.intro,'proc0_intro2.png',path.ori);
    IntroTex{3} = load_image(win,path.intro,'proc0_complete.png',path.ori);
    IntroTex{4} = load_image(win,path.intro,'proc0_rule.png',path.ori);

    % 设置指导语图片显示位置（屏幕中央）
    introRect = [center_x-600, center_y-400, center_x+600, center_y+400];
    ruleRect = [center_x+50, center_y-300, center_x+950, center_y+300];
    
%% 第一部分：自由练习
    Screen('DrawTexture', win, IntroTex{1}, [], introRect);
    Screen('Flip', win);
    key_space(key);
    
    % 自由练习阶段
    demo_free_practice(win, winRect, rgb, key, Rect_EPtask.square, IntroTex, ruleRect);
    
%% 第二部分：匹配练习
    Screen('DrawTexture', win, IntroTex{2}, [], introRect);
    Screen('Flip', win);
    key_space(key);
    
    % 匹配练习阶段（3个试次）
    demo_match_practice(win, winRect, rgb, key, Rect_EPtask.square, Ttex, TRect);
    
    % 练习结束
    Screen('DrawTexture', win, IntroTex{3}, [], introRect);
    Screen('Flip', win);
    key_space(key);
    
    sca;

catch    
    ShowCursor;
    Screen('CloseAll');
    psychrethrow(lasterror);
end


%% 子函数：自由练习
function demo_free_practice(win, winRect, rgb, key, squareRect, IntroTex, ruleRect)
    while KbCheck; end
    cfg = experiment_config();
    squareSide = squareRect(3) - squareRect(1);

    % 设置bar参数
    barWidth = round(squareSide * cfg.barWidthRatio);
    barInset = round(squareSide * cfg.barInsetRatio);
    maxBarLength = squareSide;
    leftBarLength = 0;
    rightBarLength = 0;
    stepSize = max(1, round(squareSide * cfg.barStepRatio));
    
    % 颜色定义
    squareColor = rgb.white;
    BarColor = rgb.white;
    squareBorderWidth = cfg.squareBorderWidthPx;
    
    % 初始化可移动角度
    movableAngle = pi/2;
    
    % 计算圆心位置
    centerX = squareRect(1) - round(squareSide * cfg.circleOffsetRatio);
    centerY = (squareRect(2) + squareRect(4)) / 2;
    radius = round(squareSide * cfg.circleRadiusRatio);
    
    % 固定半径参数
    fixedAngle = pi/2;
    fixedEndX = centerX + radius * cos(fixedAngle);
    fixedEndY = centerY - radius * sin(fixedAngle);
    dashLength = max(1, round(squareSide * cfg.dashLengthRatio));
    gapLength = max(1, round(squareSide * cfg.dashGapRatio));
    angleStep = deg2rad(cfg.angleStepDeg);
    
    lastKeyCode = zeros(1, 256);
    
    while true
        Screen('BlendFunction', win, 'GL_SRC_ALPHA', 'GL_ONE_MINUS_SRC_ALPHA');
        
        % 绘制正方形
        Screen('FrameRect', win, squareColor, squareRect, squareBorderWidth);
        
        % 绘制圆盘
        ptb_draw_polar_indicator(win, squareColor, centerX, centerY, radius, fixedEndX, fixedEndY, dashLength, gapLength, movableAngle);
        
        Screen('DrawTexture', win, IntroTex{4}, [], ruleRect);

        % 计算左bar的位置
        leftBarRect = [squareRect(1) + barInset, ...
                      squareRect(4) - leftBarLength, ...
                      squareRect(1) + barInset + barWidth, ...
                      squareRect(4)];
        
        % 计算右bar的位置
        rightBarRect = [squareRect(3) - barInset - barWidth, ...
                       squareRect(4) - rightBarLength, ...
                       squareRect(3) - barInset, ...
                       squareRect(4)];
        
        % 绘制bars
        Screen('FillRect', win, BarColor, leftBarRect);
        Screen('FillRect', win, BarColor, rightBarRect);
        
        % % 显示当前数值信息（帮助被试理解）- 使用英文数字
        % angleDeg = round(rad2deg(movableAngle));
        % if angleDeg > 180
        %     angleDeg = angleDeg - 360;
        % end
        % infoText = sprintf('Angle: %d  Left: %d  Right: %d', angleDeg, round(leftBarLength), round(rightBarLength));
        % Screen('DrawText', win, infoText, centerX - 100, centerY + radius + 50, rgb.white);
        
        % 刷新屏幕
        Screen('Flip', win);
        
        % 检查按键
        [keyIsDown, ~, keyCode] = KbCheck;
        
        if keyIsDown
            % ESC键退出
            if keyCode(KbName('SPACE'))
                break;
            end

            if keyCode(KbName('ESCAPE'))
                sca;
            end

            % 检测按键变化或持续按键
            keyChanged = any(keyCode ~= lastKeyCode);
            
            if keyChanged || (keyIsDown && any(keyCode([key.LeftArrow, key.RightArrow, key.UpArrow, key.DownArrow])))
                
                if keyCode(key.RightArrow)
                    movableAngle = movableAngle - angleStep;
                    if movableAngle < 0
                        movableAngle = movableAngle + 2*pi;
                    end
                end
        
                if keyCode(key.LeftArrow)
                    movableAngle = movableAngle + angleStep;
                    if movableAngle > 2*pi
                        movableAngle = movableAngle - 2*pi;
                    end
                end
        
                if keyCode(key.UpArrow)
                    potentialLeftIncrease = leftBarLength + stepSize * cos(movableAngle);
                    potentialRightIncrease = rightBarLength + stepSize * sin(movableAngle);
                    
                    if potentialLeftIncrease <= maxBarLength && potentialRightIncrease <= maxBarLength && potentialLeftIncrease >= 0 && potentialRightIncrease >=0
                        leftBarLength = potentialLeftIncrease;
                        rightBarLength = potentialRightIncrease;
                    end
                end
                
                if keyCode(key.DownArrow)
                    potentialLeftDecrease = leftBarLength - stepSize * cos(movableAngle);
                    potentialRightDecrease = rightBarLength - stepSize * sin(movableAngle);
                    
                    if potentialLeftDecrease >= 0 && potentialRightDecrease >= 0 && potentialLeftDecrease <= maxBarLength && potentialRightDecrease <= maxBarLength
                        leftBarLength = potentialLeftDecrease;
                        rightBarLength = potentialRightDecrease;
                    end
                end
                
                if keyChanged
                    WaitSecs(0.1);
                else
                    WaitSecs(0.05);
                end
            end
            
            lastKeyCode = keyCode;
        else
            lastKeyCode = zeros(1, 256);
        end
    end
end


%% 子函数：匹配练习
function demo_match_practice(win, winRect, rgb, key, squareRect, Ttex, TRect)
    cfg = experiment_config();
    squareSide = squareRect(3) - squareRect(1);

    % 设置bar参数
    barWidth = round(squareSide * cfg.barWidthRatio);
    barInset = round(squareSide * cfg.barInsetRatio);
    maxBarLength = squareSide;
    stepSize = max(1, round(squareSide * cfg.barStepRatio));
    
    % 颜色定义
    squareColor = rgb.white;
    BarColor = rgb.white;
    targetBarColor = [150, 150, 255]; % 目标bar使用淡蓝色
    squareBorderWidth = cfg.squareBorderWidthPx;
    matchTolerance = squareSide * cfg.matchToleranceRatio;
    
    % 固定半径参数
    angleStep = deg2rad(cfg.angleStepDeg);
    
    % 计算圆心位置
    centerX = squareRect(1) - round(squareSide * cfg.circleOffsetRatio);
    centerY = (squareRect(2) + squareRect(4)) / 2;
    radius = round(squareSide * cfg.circleRadiusRatio);
    
    fixedAngle = pi/2;
    fixedEndX = centerX + radius * cos(fixedAngle);
    fixedEndY = centerY - radius * sin(fixedAngle);
    dashLength = max(1, round(squareSide * cfg.dashLengthRatio));
    gapLength = max(1, round(squareSide * cfg.dashGapRatio));
    
    % 生成3个随机目标
    nTrials = 3;
    targetMin = max(1, round(maxBarLength * cfg.targetMinRatio));
    targetLeftBar = randi([targetMin, maxBarLength - targetMin], 1, nTrials);
    targetRightBar = randi([targetMin, maxBarLength - targetMin], 1, nTrials);
    
    % 计算目标bar在屏幕右侧的位置
    [center_x, ~] = RectCenter(winRect);
    targetSquareRect = [center_x + 200, squareRect(2), center_x + 200 + squareSide, squareRect(4)];
    
    for trial = 1:nTrials
        % 初始化当前试次
        leftBarLength = 0;
        rightBarLength = 0;
        movableAngle = pi/2;
        lastKeyCode = zeros(1, 256);
        
        % 当前目标
        currentTargetLeft = targetLeftBar(trial);
        currentTargetRight = targetRightBar(trial);
        
        % 提示开始 - 显示试次编号
        trialText = sprintf('Trial %d / %d', trial, nTrials);
        [center_x_temp, center_y_temp] = RectCenter(winRect);
        Screen('DrawText', win, trialText, center_x_temp - 50, center_y_temp, rgb.white);
        Screen('Flip', win);
        WaitSecs(1);
        
        while true
            Screen('BlendFunction', win, 'GL_SRC_ALPHA', 'GL_ONE_MINUS_SRC_ALPHA');
            
            % === 左侧：可调整的区域 ===
            % 绘制正方形
            Screen('FrameRect', win, squareColor, squareRect, squareBorderWidth);
            
            % 绘制圆盘
            ptb_draw_polar_indicator(win, squareColor, centerX, centerY, radius, fixedEndX, fixedEndY, dashLength, gapLength, movableAngle);
            
            % 计算左bar的位置
            leftBarRect = [squareRect(1) + barInset, ...
                          squareRect(4) - leftBarLength, ...
                          squareRect(1) + barInset + barWidth, ...
                          squareRect(4)];            
            % 计算右bar的位置
            rightBarRect = [squareRect(3) - barInset - barWidth, ...
                           squareRect(4) - rightBarLength, ...
                           squareRect(3) - barInset, ...
                           squareRect(4)];
            
            % 绘制当前bars
            Screen('FillRect', win, BarColor, leftBarRect);
            Screen('FillRect', win, BarColor, rightBarRect);
            
            % 在左侧正方形上方显示标签
            % Screen('DrawText', win, 'Current', squareRect(1) + 150, squareRect(2) - 40, rgb.white);
            
            % === 右侧：目标区域 ===
            % 绘制目标正方形
            Screen('FrameRect', win, squareColor, targetSquareRect, squareBorderWidth);
            
            % 计算目标左bar的位置
            targetLeftBarRect = [targetSquareRect(1) + barInset, ...
                                targetSquareRect(4) - currentTargetLeft, ...
                                targetSquareRect(1) + barInset + barWidth, ...
                                targetSquareRect(4)];
            
            % 计算目标右bar的位置
            targetRightBarRect = [targetSquareRect(3) - barInset - barWidth, ...
                                 targetSquareRect(4) - currentTargetRight, ...
                                 targetSquareRect(3) - barInset, ...
                                 targetSquareRect(4)];
            
            % 绘制目标bars（使用不同颜色）
            Screen('FillRect', win, targetBarColor, targetLeftBarRect);
            Screen('FillRect', win, targetBarColor, targetRightBarRect);
            
            % 在右侧正方形上方显示标签
            % Screen('DrawText', win, 'Target', targetSquareRect(1) + 150, targetSquareRect(2) - 40, rgb.white);
            
            % 检查左右是否各自匹配（基于abs差值阈值），并用图标提示（参照 demo_EPtask 的呈现）
            leftMatch = (abs(leftBarLength - currentTargetLeft) <= matchTolerance);
            rightMatch = (abs(rightBarLength - currentTargetRight) <= matchTolerance);

            % 计算图标绘制位置：在目标正方形上方居中显示一个小图标
            [targetCenterX, targetCenterY] = RectCenter(targetSquareRect);
            iconW = 200; iconH = 100; % 图标尺寸（可按需调整）
            iconRect = [targetCenterX - iconW/2, targetSquareRect(2) - iconH - 20, targetCenterX + iconW/2, targetSquareRect(2) - 20];

            % 根据匹配情况绘制对应的提示图（Ttex: 1=left, 2=right, 3=both）
            if leftMatch && rightMatch
                % 两侧都匹配：全部匹配图标
                Screen('DrawTexture', win, Ttex{3}, [], iconRect);
            elseif leftMatch && ~rightMatch
                % 仅左侧匹配
                Screen('DrawTexture', win, Ttex{1}, [], iconRect);
            elseif rightMatch && ~leftMatch
                % 仅右侧匹配
                Screen('DrawTexture', win, Ttex{2}, [], iconRect);
            else
                % 无匹配时不显示图标（保持界面简洁）
                % 也可在此处绘制一个灰色或提示图
            end

            % % 仍然显示数值差异信息以便被试校准（放在目标正方形下方）
            % statusText = sprintf('Left diff: %d  Right diff: %d', ...
            %     round(abs(leftBarLength - currentTargetLeft)), ...
            %     round(abs(rightBarLength - currentTargetRight)));
            % statusColor = rgb.white;
            % [center_x_temp, ~] = RectCenter(winRect);
            % Screen('DrawText', win, statusText, center_x_temp - 150, squareRect(4) + 80, statusColor);
            
            % 刷新屏幕
            Screen('Flip', win);
            
            % 检查按键
            [keyIsDown, ~, keyCode] = KbCheck;
            
            if keyIsDown
                % 如果匹配成功且按下空格，进入下一试次
                if leftMatch && rightMatch && keyCode(key.space)
                    WaitSecs(0.2);
                    break;
                end

                if keyCode(key.esc)
                    sca;   
                    break;
                end

                % 检测按键变化或持续按键
                keyChanged = any(keyCode ~= lastKeyCode);
                
                if keyChanged || (keyIsDown && any(keyCode([key.LeftArrow, key.RightArrow, key.UpArrow, key.DownArrow])))
                    
                    if keyCode(key.RightArrow)
                        movableAngle = movableAngle - angleStep;
                        if movableAngle < 0
                            movableAngle = movableAngle + 2*pi;
                        end
                    end
            
                    if keyCode(key.LeftArrow)
                        movableAngle = movableAngle + angleStep;
                        if movableAngle > 2*pi
                            movableAngle = movableAngle - 2*pi;
                        end
                    end
            
                    if keyCode(key.UpArrow)
                        potentialLeftIncrease = leftBarLength + stepSize * cos(movableAngle);
                        potentialRightIncrease = rightBarLength + stepSize * sin(movableAngle);
                        
                        if potentialLeftIncrease <= maxBarLength && potentialRightIncrease <= maxBarLength && potentialLeftIncrease >= 0 && potentialRightIncrease >=0
                            leftBarLength = potentialLeftIncrease;
                            rightBarLength = potentialRightIncrease;
                        end
                    end
                    
                    if keyCode(key.DownArrow)
                        potentialLeftDecrease = leftBarLength - stepSize * cos(movableAngle);
                        potentialRightDecrease = rightBarLength - stepSize * sin(movableAngle);
                        
                        if potentialLeftDecrease >= 0 && potentialRightDecrease >= 0 && potentialLeftDecrease <= maxBarLength && potentialRightDecrease <= maxBarLength
                            leftBarLength = potentialLeftDecrease;
                            rightBarLength = potentialRightDecrease;
                        end
                    end
                    
                    if keyChanged
                        WaitSecs(0.1);
                    else
                        WaitSecs(0.05);
                    end
                end
                
                lastKeyCode = keyCode;
            else
                lastKeyCode = zeros(1, 256);
            end
        end
    end
end

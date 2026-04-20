function [test, learnData] = demo_EPtask(win,winRect,rgb,key,squareRect,Ftex,FRect,Ttex,TRect,facebar,test)
    try
        cfg = experiment_config();
        squareSide = squareRect(3) - squareRect(1);

        % 设置bar参数
        barWidth = round(squareSide * cfg.barWidthRatio); % bar的宽度
        barInset = round(squareSide * cfg.barInsetRatio);
        maxBarLength = squareSide; % bar的最大长度
        leftBarLength = 0; % 左bar初始长度
        rightBarLength = 0; % 右bar初始长度
        stepSize = max(1, round(squareSide * cfg.barStepRatio)); % 每次按键变化的步长
        
        % 颜色定义
        squareColor = rgb.white;
        BarColor = rgb.white;
        squareBorderWidth = cfg.squareBorderWidthPx;
        matchTolerance = squareSide * cfg.matchToleranceRatio;

        % 面孔呈现位置随机
        position = shuffle(1:6);
        lastKeyCode = zeros(1, 256);
        
        % 初始化可移动角度（固定在90度，竖直向上）
        movableAngle = pi/2;
        
        % 初始化学习数据记录
        learnData = [];
        recordIdx = 1;
        startTime = GetSecs; % 记录学习开始时间
        
        % 计算圆心位置（正方形左侧中心）
        centerX = squareRect(1) - round(squareSide * cfg.circleOffsetRatio);
        centerY = (squareRect(2) + squareRect(4)) / 2; % 垂直居中
        radius = round(squareSide * cfg.circleRadiusRatio); % 圆的半径
        
        % 固定半径（竖直向上，虚线）参数
        fixedAngle = pi/2; % 90度，竖直向上
        fixedEndX = centerX + radius * cos(fixedAngle);
        fixedEndY = centerY - radius * sin(fixedAngle); % 注意：屏幕坐标系Y轴向下为正
        dashLength = max(1, round(squareSide * cfg.dashLengthRatio)); % 虚线段长度
        gapLength = max(1, round(squareSide * cfg.dashGapRatio));  % 虚线间隔长度
        angleStep = deg2rad(cfg.angleStepDeg); %角度步长
        
        while true
            % 设置全局颜色
            Screen('BlendFunction', win, 'GL_SRC_ALPHA', 'GL_ONE_MINUS_SRC_ALPHA');

            % 绘制面孔
            for i = 1:6
                if norm(facebar(i,:)-[leftBarLength rightBarLength]) <= matchTolerance
                    brightness = 1; % 0-1范围
                    Screen('Drawtexture',win,Ftex{i},[],FRect(position(i),:), 0, [], brightness);
                    Screen('Drawtexture',win,Ttex{3},[],TRect(position(i),:));
                elseif abs(facebar(i,1)-leftBarLength) <= matchTolerance && abs(facebar(i,2)-rightBarLength) > matchTolerance
                    brightness = 1; % 0-1范围
                    Screen('Drawtexture',win,Ftex{i},[],FRect(position(i),:), 0, [], brightness);
                    Screen('Drawtexture',win,Ttex{1},[],TRect(position(i),:));
                elseif abs(facebar(i,2)-rightBarLength) <= matchTolerance && abs(facebar(i,1)-leftBarLength) > matchTolerance
                    brightness = 1; % 0-1范围
                    Screen('Drawtexture',win,Ftex{i},[],FRect(position(i),:), 0, [], brightness);
                    Screen('Drawtexture',win,Ttex{2},[],TRect(position(i),:));
                else
                    brightness = 0.5; % 0-1范围
                    Screen('Drawtexture',win,Ftex{i},[],FRect(position(i),:), 0, [], brightness);
                end
            end

            % 绘制正方形
            Screen('FrameRect', win, squareColor, squareRect, squareBorderWidth);

            % 绘制圆盘
            ptb_draw_polar_indicator(win, squareColor, centerX, centerY, radius, fixedEndX, fixedEndY, dashLength, gapLength, movableAngle);
                
            % 计算左bar的位置（左侧）
            leftBarRect = [squareRect(1) + barInset, ...
                          squareRect(4) - leftBarLength, ...
                          squareRect(1) + barInset + barWidth, ...
                          squareRect(4)];
                
            % 计算右bar的位置（右侧）
            rightBarRect = [squareRect(3) - barInset - barWidth, ...
                           squareRect(4) - rightBarLength, ...
                           squareRect(3) - barInset, ...
                           squareRect(4)];
                
            % 绘制bars
            Screen('FillRect', win, BarColor, leftBarRect);
            Screen('FillRect', win, BarColor, rightBarRect);
            
            % % 显示当前角度信息（在圆盘下方）
            % angleDeg = round(rad2deg(movableAngle));
            % angleText = sprintf('Angle: %d°', angleDeg);
            % textY = centerY + radius + 30; % 圆盘下方30像素
            % DrawFormattedText(win, angleText, centerX - 50, textY, rgb.white);
            % 
            % % 显示Bar长度信息
            % lengthText = sprintf('Left: %d/%d  Right: %d/%d', leftBarLength, maxBarLength, rightBarLength, maxBarLength);
            % DrawFormattedText(win, lengthText, centerX - 100, textY + 30, rgb.white);

            % 刷新屏幕
            Screen('Flip', win);
            
            % 检查按键
            [keyIsDown, ~, keyCode] = KbCheck;
            
            if keyIsDown
                % ESC键退出
                if keyCode(KbName('ESCAPE'))
                    test = -1;
                    break;
                end

                % q键进入测试
                if keyCode(KbName('q'))
                    test = 1;
                    break;
                end
                
                % 检测按键变化或持续按键
                keyChanged = any(keyCode ~= lastKeyCode);
                
                if keyChanged || (keyIsDown && any(keyCode([key.LeftArrow, key.RightArrow, key.UpArrow, key.DownArrow])))
                    
                    if keyCode(key.RightArrow)
                        % 右键：顺时针增加角度
                        movableAngle = movableAngle - angleStep; % 约2.86度
                        if movableAngle < 0
                            movableAngle = movableAngle + 2*pi;
                        end
                    end
            
                    if keyCode(key.LeftArrow)
                        % 左键：逆时针减小角度
                        movableAngle = movableAngle + angleStep; % 约2.86度
                        if movableAngle > 2*pi
                            movableAngle = movableAngle - 2*pi;
                        end
                    end
            
                    if keyCode(key.UpArrow)
                        % 计算按上键后的潜在新长度
                        potentialLeftIncrease = leftBarLength + stepSize * cos(movableAngle);
                        potentialRightIncrease = rightBarLength + stepSize * sin(movableAngle);
                        
                        % 只有当两个bar都未达到上限时才响应
                        if potentialLeftIncrease <= maxBarLength && potentialRightIncrease <= maxBarLength && potentialLeftIncrease >= 0 && potentialRightIncrease >=0
                            leftBarLength = potentialLeftIncrease;
                            rightBarLength = potentialRightIncrease;
                            % 记录坐标点和时间戳
                            learnData(recordIdx).leftBar = leftBarLength;
                            learnData(recordIdx).rightBar = rightBarLength;
                            learnData(recordIdx).timestamp = GetSecs - startTime;
                            recordIdx = recordIdx + 1;
                        end
                        % 如果任意一个bar达到上限，就不做任何操作
                    end
                    
                    if keyCode(key.DownArrow)
                        % 计算按下键后的潜在新长度
                        potentialLeftDecrease = leftBarLength - stepSize * cos(movableAngle);
                        potentialRightDecrease = rightBarLength - stepSize * sin(movableAngle);
                        
                        % 只有当两个bar都未达到下限时才响应
                        if potentialLeftDecrease >= 0 && potentialRightDecrease >= 0 && potentialLeftDecrease <= maxBarLength && potentialRightDecrease <= maxBarLength
                            leftBarLength = potentialLeftDecrease;
                            rightBarLength = potentialRightDecrease;
                            % 记录坐标点和时间戳
                            learnData(recordIdx).leftBar = leftBarLength;
                            learnData(recordIdx).rightBar = rightBarLength;
                            learnData(recordIdx).timestamp = GetSecs - startTime;
                            recordIdx = recordIdx + 1;
                        end
                        % 如果任意一个bar达到下限，就不做任何操作
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
        
        if test==1
            Text='Test Begin'; %需要呈现的文字
            [center_x,center_y] = RectCenter(winRect);
            % 设置文字大小
            oldTextSize = Screen('TextSize', win, 35);
            % 计算文字在屏幕中央的位置
            [normBoundsRect, ~] = Screen('TextBounds', win, Text);
            textWidth = normBoundsRect(3);  % 文字宽度
            textHeight = normBoundsRect(4); % 文字高度
            % 计算文字绘制位置（使文字中心在屏幕中心）
            xPos = center_x - textWidth/2;
            yPos = center_y - textHeight/2;
            Screen('DrawText', win, Text, xPos, yPos, [225 225 225]);
            Screen('Flip', win);
            WaitSecs(1);
        end
        
    catch ME
        % 错误处理
        sca;
        rethrow(ME);
    end
end

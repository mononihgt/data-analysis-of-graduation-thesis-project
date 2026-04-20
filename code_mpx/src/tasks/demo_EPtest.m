function [test,result] = demo_EPtest(win,winRect,rgb,squareRect,key,Ftex,FRect,facebar,test,subinfo,Wtex)
    cfg = experiment_config();
    squareSide = squareRect(3) - squareRect(1);

    % 初始化可移动角度（固定在90度，竖直向上）
    movableAngle = pi/2;

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
    
    % 设置bar参数
    barWidth = round(squareSide * cfg.barWidthRatio); % bar的宽度
    barInset = round(squareSide * cfg.barInsetRatio);
    maxBarLength = squareSide; % bar的最大长度
    stepSize = max(1, round(squareSide * cfg.barStepRatio)); % 每次按键变化的步长
    
    % 颜色定义
    squareColor = rgb.white;
    BarColor = rgb.white;
    squareBorderWidth = cfg.squareBorderWidthPx;
    matchTolerance = squareSide * cfg.matchToleranceRatio;
    % 获取屏幕中心
    [screenX, screenY] = Screen('WindowSize', win);
    
    % 计算居中位置
    cX = screenX / 2;
    cY = screenY / 2;
    
    % 创建居中的矩形
    [textureWidth, textureHeight] = Screen('WindowSize', Wtex{1});
    FRect_centered = [cX - textureWidth/2, cY - textureHeight/2, ...
                      cX + textureWidth/2, cY + textureHeight/2];
    result=[];

    % 初始化test_time
    test_time = 1;

    while test==1
        % 试次表
        triallist = shuffle(1:6);

        for i=1:6
            leftBarLength = 0; % 左bar初始长度
            rightBarLength = 0; % 右bar初始长度
            movableAngle = pi/2;
            
            % 初始化上一次按键状态
            lastKeyCode = zeros(1, 256);
            
            % 初始显示
            Screen('Drawtexture',win,Ftex{triallist(i)},[],FRect);
            Screen('FrameRect', win, squareColor, squareRect, squareBorderWidth);

            % % 显示当前角度信息（在圆盘下方）
            % angleDeg = round(rad2deg(movableAngle));
            % angleText = sprintf('Angle: %d°', angleDeg);
            % textY = centerY + radius + 30; % 圆盘下方30像素
            % DrawFormattedText(win, angleText, centerX - 50, textY, rgb.white);
            % 
            % % 显示Bar长度信息
            % lengthText = sprintf('Left: %d/%d  Right: %d/%d', leftBarLength, maxBarLength, rightBarLength, maxBarLength);
            % DrawFormattedText(win, lengthText, centerX - 100, textY + 30, rgb.white);

            
            % 重新计算bar位置（初始状态）
            leftBarRect = [squareRect(1) + barInset, ...
                          squareRect(4) - leftBarLength, ...
                          squareRect(1) + barInset + barWidth, ...
                          squareRect(4)];
            rightBarRect = [squareRect(3) - barInset - barWidth, ...
                           squareRect(4) - rightBarLength, ...
                           squareRect(3) - barInset, ...
                           squareRect(4)];
            
            Screen('FillRect', win, BarColor, leftBarRect);
            Screen('FillRect', win, BarColor, rightBarRect);
            
            % 绘制圆盘
            ptb_draw_polar_indicator(win, squareColor, centerX, centerY, radius, fixedEndX, fixedEndY, dashLength, gapLength, movableAngle);
                
            % 刷新屏幕
            TSecs = Screen('Flip', win);

            while true
                % 检查按键
                [keyIsDown, key_secs, keyCode] = KbCheck;
                
                if keyIsDown
                    % ESC键退出 - 立即检测
                    if keyCode(KbName('ESCAPE'))
                        test = -1;
                        break;
                    % q键进入学习 - 立即检测
                    elseif keyCode(KbName('q'))
                        test = 0;
                        break;
                    end
                    
                    keyChanged = any(keyCode ~= lastKeyCode);

                    % 只对上下左右箭头键进行持续按键检测
                    if keyChanged || (keyIsDown && any(keyCode([key.LeftArrow, key.RightArrow, key.UpArrow, key.DownArrow])))
                        % 检测按键变化或持续按键                        
                        if keyChanged || keyIsDown
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
                                end
                                % 如果任意一个bar达到下限，就不做任何操作
                            end 

                            % 更新显示
                            Screen('Drawtexture',win,Ftex{triallist(i)},[],FRect);
                            Screen('FrameRect', win, squareColor, squareRect, squareBorderWidth);
                            
                            % 重新计算bar位置
                            leftBarRect = [squareRect(1) + barInset, ...
                                          squareRect(4) - leftBarLength, ...
                                          squareRect(1) + barInset + barWidth, ...
                                          squareRect(4)];
                            rightBarRect = [squareRect(3) - barInset - barWidth, ...
                                           squareRect(4) - rightBarLength, ...
                                           squareRect(3) - barInset, ...
                                           squareRect(4)];
                            
                            Screen('FillRect', win, BarColor, leftBarRect);
                            Screen('FillRect', win, BarColor, rightBarRect);
                            
                            % 绘制圆盘
                            ptb_draw_polar_indicator(win, squareColor, centerX, centerY, radius, fixedEndX, fixedEndY, dashLength, gapLength, movableAngle);

                            Screen('Flip', win);
                            
                            % 如果是新按下的键，等待一小段时间后开始连续变化
                            if keyChanged
                                WaitSecs(0.1); % 初始延迟
                            else
                                WaitSecs(0.05); % 连续变化延迟
                            end
                        end
                    end
                    
                    % 空格确认 - 记录当前条形长度并进入下一个试次
                    if keyCode(KbName('SPACE'))
                        rt = key_secs - TSecs;
                        % 判断条形长度是否正确
                        if norm(facebar(triallist(i),:) - [leftBarLength rightBarLength]) <= matchTolerance
                            Screen('Drawtexture',win,Wtex{1},[],FRect_centered);
                            % 显示正确/错误反馈
                            Screen('Flip', win);
                            WaitSecs(2); % 显示反馈2秒
                
                            if str2double(char(subinfo(2))) == 1
                                Gender = 'Male';
                            else
                                Gender = 'Female';
                            end
                            %-------------------------------------------
                            if str2double(char(subinfo(5))) == 1
                                Handedness = 'Right';
                            else
                                Handedness = 'Left';
                            end
                            
                            % 修复结果记录索引问题
                            currentIndex = (test_time-1)*6 + i;
                            result(currentIndex,1).SubNo = str2double(char(subinfo(1)));
                            result(currentIndex,1).Name = char(subinfo(4));
                            result(currentIndex,1).Gender = Gender;
                            result(currentIndex,1).Age = str2double(char(subinfo(3)));
                            result(currentIndex,1).Handedness = Handedness;
                            result(currentIndex,1).test_time = test_time;
                            result(currentIndex,1).true_leftBar = facebar(triallist(i),1);
                            result(currentIndex,1).true_rightBar = facebar(triallist(i),2);  
                            result(currentIndex,1).leftBarLength = leftBarLength;
                            result(currentIndex,1).rightBarLength = rightBarLength;
                            result(currentIndex,1).face = triallist(i);  
                            result(currentIndex,1).acc = 1;
                            result(currentIndex,1).rt = rt;
                        else
                            Screen('Drawtexture',win,Wtex{2},[],FRect_centered);
                            % 显示正确/错误反馈
                            Screen('Flip', win);
                            WaitSecs(2); % 显示反馈2秒
                            if str2double(char(subinfo(2))) == 1
                                Gender = 'Male';
                            else
                                Gender = 'Female';
                            end
                            if str2double(char(subinfo(5))) == 1
                                Handedness = 'Right';
                            else
                                Handedness = 'Left';
                            end
                            
                            currentIndex = (test_time-1)*6 + i;
                            result(currentIndex,1).SubNo = str2double(char(subinfo(1)));
                            result(currentIndex,1).Name = char(subinfo(4));
                            result(currentIndex,1).Gender = Gender;
                            result(currentIndex,1).Age = str2double(char(subinfo(3)));
                            result(currentIndex,1).Handedness = Handedness;
                            result(currentIndex,1).test_time = test_time;
                            result(currentIndex,1).true_leftBar = facebar(triallist(i),1);
                            result(currentIndex,1).true_rightBar = facebar(triallist(i),2);  
                            result(currentIndex,1).leftBarLength = leftBarLength;
                            result(currentIndex,1).rightBarLength = rightBarLength;
                            result(currentIndex,1).face = triallist(i); 
                            result(currentIndex,1).acc = 0;
                            result(currentIndex,1).rt = rt;
                        end
                
                        break;
                    end
                    
                    % 更新上一次的按键状态
                    lastKeyCode = keyCode;
                else
                    % 没有按键时重置状态
                    lastKeyCode = zeros(1, 256);
                end   
            end
            
            % 每完成一个试次后立即检查是否连续6个试次正确
            n = length(result);
            
            x = 6;

            if n >= x
                last6Values = [result(n-(x-1):n).acc];
                grade = all(last6Values == 1);
                if grade == 1
                    % 给出通过提示并设置test为-1以便调用者结束测试
                    Text = 'Test Passed';
                    [center_x,center_y] = RectCenter(winRect);
                    Screen('TextSize', win, 35);
                    [normBoundsRect, ~] = Screen('TextBounds', win, Text);
                    textWidth = normBoundsRect(3);
                    textHeight = normBoundsRect(4);
                    xPos = center_x - textWidth/2;
                    yPos = center_y - textHeight/2;
                    Screen('DrawText', win, Text, xPos, yPos, [225 225 225]);
                    Screen('Flip', win);
                    WaitSecs(1);
                    test = -1; % signal to caller to exit/close
                    break;
                end
            end
            
            if test == -1 || test == 0
                break;
            end
        end

        if test == -1 || test == 0
            break;
        end

        test_time = test_time + 1;
    end
    
    if test==0
        Text='Return learning'; % 需要呈现的文字
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

end

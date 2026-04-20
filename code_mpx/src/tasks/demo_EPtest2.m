function result = demo_EPtest2(win,winRect,rgb,squareRect,key,Ftex,FRect,facebar,subinfo)
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
    result=[];
    test=1;

    % 试次表（重复4次）
    for n=1:4
        triallist(6*(n-1)+1:6*n,1) = shuffle(1:6);
    end

    for i=1:length(triallist)
        if test==-1
            break;
        end

        Text='+'; %需要呈现的文字
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
        Screen('DrawText', win, Text, xPos, yPos, [255, 255, 255]);
        Screen('Flip', win);
        WaitSecs(1);


        leftBarLength = 0; % 左bar初始长度
        rightBarLength = 0; % 右bar初始长度
        movableAngle = pi/2;

        
        % 初始化上一次按键状态
        lastKeyCode = zeros(1, 256);
                    
        Screen('Drawtexture',win,Ftex{triallist(i)},[],FRect);
    
        % 绘制正方形
        Screen('FrameRect', win, squareColor, squareRect, squareBorderWidth);
            
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
                end
                
                % 只对上下左右箭头键进行持续按键检测
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
 
                        % 如果是新按下的键，等待一小段时间后开始连续变化
                        if keyChanged
                            WaitSecs(0.1); % 初始延迟
                        else
                            WaitSecs(0.05); % 连续变化延迟
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
                    end
                end
                
                % 空格确认 - 记录当前条形长度并进入下一个试次
                if keyCode(KbName('SPACE'))
                    rt = key_secs - TSecs;
                    % 判断条形长度是否正确
                    if norm(facebar(triallist(i),:) - [leftBarLength rightBarLength]) <= matchTolerance     
                        acc = 1;
                    else
                        acc = 0;
                    end
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
                    result(i,1).SubNo = str2double(char(subinfo(1)));
                    result(i,1).Name = char(subinfo(4));
                    result(i,1).Gender = Gender;
                    result(i,1).Age = str2double(char(subinfo(3)));
                    result(i,1).Handedness = Handedness;
                    result(i,1).face = triallist(i); 
                    result(i,1).true_leftBar = facebar(triallist(i),1);
                    result(i,1).true_rightBar = facebar(triallist(i),2);  
                    result(i,1).leftBarLength = leftBarLength;
                    result(i,1).rightBarLength = rightBarLength;  
                    result(i,1).error = norm([leftBarLength rightBarLength]-[facebar(triallist(i),1) facebar(triallist(i),2)]);
                    result(i,1).acc = acc;
                    result(i,1).rt = rt;
                    break;
                end
                
                % 更新上一次的按键状态
                lastKeyCode = keyCode;
            else
                % 没有按键时重置状态
                lastKeyCode = zeros(1, 256);
            end   
        end
    end
    
end

function result=demo_PDtask(triallist,win,winRect,rgb,key,Ftex,FRect,dif_tex,mean_tex,mean_mean_tex,introRect,squareRect,subinfo)
    cfg = experiment_config();
    squareSide = squareRect(3) - squareRect(1);

    % 设置bar参数
    barWidth = round(squareSide * cfg.barWidthRatio); % bar的宽度
    barInset = round(squareSide * cfg.barInsetRatio);
    maxBarLength = squareSide; % bar的最大长度
    stepSize = max(1, round(squareSide * cfg.barStepRatio)); % 每次按键变化的步长

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
    
    % 颜色定义
    squareColor = rgb.white;
    BarColor = rgb.white;
    squareBorderWidth = cfg.squareBorderWidthPx;
    mmean_Rect = [introRect(1) introRect(2)-350 introRect(3) introRect(4)-350];

    exit=0;

    for i=1:length(triallist)

        if exit==1
            break;
        end
        
        % 初始化可移动角度（固定在90度，竖直向上）
        movableAngle = pi/2;
    
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
        
        % 初始化上一次按键状态
        lastKeyCode = zeros(1, 256);
                    
        Screen('Drawtexture',win,Ftex{triallist(i).F1},[],FRect(1,:));
        Screen('Drawtexture',win,Ftex{triallist(i).F2},[],FRect(2,:));
    
        % 绘制正方形
        Screen('FrameRect', win, squareColor, squareRect, squareBorderWidth);
            
        % 计算左bar的位置（左侧）
        leftBarRect = [squareRect(1) + barInset, ... % 距离左边50像素
                      squareRect(4) - leftBarLength, ...
                      squareRect(1) + barInset + barWidth, ...
                      squareRect(4)];
            
        % 计算右bar的位置（右侧）
        rightBarRect = [squareRect(3) - barInset - barWidth, ... % 距离右边50像素
                       squareRect(4) - rightBarLength, ...
                       squareRect(3) - barInset, ...
                       squareRect(4)];
            
        % 绘制bars
        Screen('FillRect', win, BarColor, leftBarRect);
        Screen('FillRect', win, BarColor, rightBarRect);

        % 距离复现
        Screen('Drawtexture',win,dif_tex,[],introRect);

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
                    exit = 1;
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

                        % 如果是新按下的键，等待一小段时间后开始连续变化
                        if keyChanged
                            WaitSecs(0.1); % 初始延迟
                        else
                            WaitSecs(0.05); % 连续变化延迟
                        end
                    
                        % 更新显示
                        Screen('Drawtexture',win,Ftex{triallist(i).F1},[],FRect(1,:));
                        Screen('Drawtexture',win,Ftex{triallist(i).F2},[],FRect(2,:));
                        Screen('FrameRect', win, squareColor, squareRect, squareBorderWidth);
                        Screen('Drawtexture',win,dif_tex,[],introRect);
                        
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
                    result(i,1).F1=triallist(i,1).F1;
                    result(i,1).F1V=triallist(i,1).F1V;
                    result(i,1).F1X=triallist(i,1).F1X;
                    result(i,1).F1Y=triallist(i,1).F1Y;
                    result(i,1).F2=triallist(i,1).F2;
                    result(i,1).F2V=triallist(i,1).F2V;
                    result(i,1).F2X=triallist(i,1).F2X;
                    result(i,1).F2Y=triallist(i,1).F2Y;
                    result(i,1).D=triallist(i,1).D;
                    result(i,1).MidX=triallist(i,1).MidX;
                    result(i,1).MidY=triallist(i,1).MidY;
                    result(i,1).Mtask=triallist(i,1).Mtask;
                    result(i,1).DX=leftBarLength;
                    result(i,1).DY=rightBarLength;
                    result(i,1).ans_D=norm([leftBarLength,rightBarLength]-[0,0]);
                    result(i,1).rt1=rt;
                    break;
                end
                    
                % 更新上一次的按键状态
                lastKeyCode = keyCode;
            else
                % 没有按键时重置状态
                lastKeyCode = zeros(1, 256);
            end   
        end

        if exit==1
            break;
        end

    if triallist(i).Mtask~=0
        %% 中点值
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
        WaitSecs(0.5);

        % 初始化可移动角度（固定在90度，竖直向上）
        movableAngle = pi/2;

        %% 复现中点
        leftBarLength = 0; % 左bar初始长度
        rightBarLength = 0; % 右bar初始长度
        
        % 初始化上一次按键状态
        lastKeyCode = zeros(1, 256);
                    
        Screen('Drawtexture',win,Ftex{triallist(i).F1},[],FRect(1,:));
        Screen('Drawtexture',win,Ftex{triallist(i).F2},[],FRect(2,:));
    
        % 绘制正方形
        Screen('FrameRect', win, squareColor, squareRect, squareBorderWidth);
            
        % 计算左bar的位置（左侧）
        leftBarRect = [squareRect(1) + barInset, ... % 距离左边50像素
                      squareRect(4) - leftBarLength, ...
                      squareRect(1) + barInset + barWidth, ...
                      squareRect(4)];
            
        % 计算右bar的位置（右侧）
        rightBarRect = [squareRect(3) - barInset - barWidth, ... % 距离右边50像素
                       squareRect(4) - rightBarLength, ...
                       squareRect(3) - barInset, ...
                       squareRect(4)];
            
        % 绘制bars
        Screen('FillRect', win, BarColor, leftBarRect);
        Screen('FillRect', win, BarColor, rightBarRect);

        % 绘制圆盘
        ptb_draw_polar_indicator(win, squareColor, centerX, centerY, radius, fixedEndX, fixedEndY, dashLength, gapLength, movableAngle);

        % 距离复现
        Screen('Drawtexture',win,mean_tex,[],introRect);
    
        % 刷新屏幕
        TSecs = Screen('Flip', win);
        
        while true
            % 检查按键
            [keyIsDown, key_secs, keyCode] = KbCheck;
            
            if keyIsDown
                % ESC键退出 - 立即检测
                if keyCode(KbName('ESCAPE'))
                    exit = 1;
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
                            
                        % 如果是新按下的键，等待一小段时间后开始连续变化
                        if keyChanged
                            WaitSecs(0.1); % 初始延迟
                        else
                            WaitSecs(0.05); % 连续变化延迟
                        end
                        
                        % 更新显示
                        Screen('Drawtexture',win,Ftex{triallist(i).F1},[],FRect(1,:));
                        Screen('Drawtexture',win,Ftex{triallist(i).F2},[],FRect(2,:));
                        Screen('FrameRect', win, squareColor, squareRect, squareBorderWidth);
                        Screen('Drawtexture',win,mean_tex,[],introRect);
                        
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
                    result(i,1).MX=leftBarLength;
                    result(i,1).MY=rightBarLength;
                    result(i,1).rt2=rt;
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

        if exit==1
            break;
        end

        %% 中点值的中点值
        if triallist(i).Mtask == 2
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
            WaitSecs(0.5);
    
            % 初始化可移动角度（固定在90度，竖直向上）
            movableAngle = pi/2;
           
            %% 复现中点
            leftBarLength = 0; % 左bar初始长度
            rightBarLength = 0; % 右bar初始长度
            
            % 初始化上一次按键状态
            lastKeyCode = zeros(1, 256);
        
            % 计算4张面孔的显示位置（在mmean_Rect上方，两行排列）
            % 上一行：上一试次(i-1)的两张面孔
            % 下一行：当前试次(i)的两张面孔
            faceSize = 120; % 面孔图片尺寸
            faceGap = 50;   % 面孔之间的间隔
            facesTopY = mmean_Rect(2) - faceSize; % 4张面孔区域顶部Y坐标
            
            % 当前试次的两张面孔位置（前面）
            currFace1Rect = [mmean_Rect(1) + 0.5*faceSize+50, facesTopY, ...
                            mmean_Rect(1) + 1.5*faceSize+50, facesTopY + faceSize];
            currFace2Rect = [mmean_Rect(1) + 1.5*faceSize + faceGap+50, facesTopY, ...
                            mmean_Rect(1) + 2.5*faceSize + faceGap+50, facesTopY + faceSize];

            % 上一试次的两张面孔位置（后面）
            prevFace1Rect = [mmean_Rect(1) + 2.5*faceSize + faceGap/2 + 5*faceGap + 50, facesTopY, ...
                            mmean_Rect(1) + 3.5*faceSize + faceGap/2 + 5*faceGap + 50, facesTopY + faceSize];
            prevFace2Rect = [mmean_Rect(1) + 3.5*faceSize + faceGap/2 + 6*faceGap + 50, facesTopY, ...
                            mmean_Rect(1) + 4.5*faceSize + faceGap/2 + 6*faceGap + 50, facesTopY + faceSize];
            
            
            % 绘制上一试次(i-1)的两张面孔
            Screen('Drawtexture',win,Ftex{triallist(i-1).F1},[],prevFace1Rect);
            Screen('Drawtexture',win,Ftex{triallist(i-1).F2},[],prevFace2Rect);
            
            % 绘制当前试次(i)的两张面孔
            Screen('Drawtexture',win,Ftex{triallist(i).F1},[],currFace1Rect);
            Screen('Drawtexture',win,Ftex{triallist(i).F2},[],currFace2Rect);
        
            % 绘制正方形
            Screen('FrameRect', win, squareColor, squareRect, squareBorderWidth);
                
            % 计算左bar的位置（左侧）
            leftBarRect = [squareRect(1) + barInset, ... % 距离左边50像素
                          squareRect(4) - leftBarLength, ...
                          squareRect(1) + barInset + barWidth, ...
                          squareRect(4)];
                
            % 计算右bar的位置（右侧）
            rightBarRect = [squareRect(3) - barInset - barWidth, ... % 距离右边50像素
                           squareRect(4) - rightBarLength, ...
                           squareRect(3) - barInset, ...
                           squareRect(4)];
                
            % 绘制bars
            Screen('FillRect', win, BarColor, leftBarRect);
            Screen('FillRect', win, BarColor, rightBarRect);

            % 绘制圆盘
            ptb_draw_polar_indicator(win, squareColor, centerX, centerY, radius, fixedEndX, fixedEndY, dashLength, gapLength, movableAngle);
    
            % 中点的中点复现
            Screen('Drawtexture',win,mean_mean_tex,[],mmean_Rect);
 
            % 刷新屏幕
            TSecs = Screen('Flip', win);
            
            while true
                % 检查按键
                [keyIsDown, key_secs, keyCode] = KbCheck;
                
                if keyIsDown
                    % ESC键退出 - 立即检测
                    if keyCode(KbName('ESCAPE'))
                        exit = 1;
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
                                    
                            % 如果是新按下的键，等待一小段时间后开始连续变化
                            if keyChanged
                                WaitSecs(0.1); % 初始延迟
                            else
                                WaitSecs(0.05); % 连续变化延迟
                            end
                            
                            % 更新显示
                            % 绘制上一试次(i-1)的两张面孔
                            Screen('Drawtexture',win,Ftex{triallist(i-1).F1},[],prevFace1Rect);
                            Screen('Drawtexture',win,Ftex{triallist(i-1).F2},[],prevFace2Rect);
                            
                            % 绘制当前试次(i)的两张面孔
                            Screen('Drawtexture',win,Ftex{triallist(i).F1},[],currFace1Rect);
                            Screen('Drawtexture',win,Ftex{triallist(i).F2},[],currFace2Rect);
                            
                            Screen('FrameRect', win, squareColor, squareRect, squareBorderWidth);
                            Screen('Drawtexture',win,mean_mean_tex,[],mmean_Rect);
                            
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
                        result(i,1).MMX=leftBarLength;
                        result(i,1).MMY=rightBarLength;
                        result(i,1).rt3=rt;
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
end

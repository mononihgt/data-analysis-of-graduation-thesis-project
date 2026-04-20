function result=point_reconstruct(win,Ftex,FRect,line,dot,Xrange,Yrange,position)
    
% 圆点设置
dotSize = 10;
dotColor = [255 0 0]; % 初始红色

% 面孔状态
numFaces=6;
faceSelected = false; % 是否有面孔被选中
currentFace = 0; % 当前选中的面孔索引
faceHasDot = false(1, numFaces); % 记录每个面孔是否有对应的圆点
faceDotPositions = zeros(numFaces, 2); % 存储每个面孔对应的圆点位置
faceDotColors = zeros(numFaces, 3); % 存储每个面孔对应的圆点颜色
village = zeros(1, numFaces); % 预分配village数组
faceBorderColors = repmat([128 128 128], numFaces, 1); % 存储每个面孔的边框颜色，默认灰色
currentDotColor = [128 128 128]; % 当前选中面孔的实时颜色，默认灰色
villageSelected = false; % 标记是否已通过按键选择了村庄

experimentDone = false;
mouseWasDown = false; % 用于检测鼠标单击事件

while ~experimentDone
    % 获取鼠标位置和状态
    [x, y, buttons] = GetMouse(win);
    mouseIsDown = any(buttons);
    
    % 检查鼠标是否在矩形区域内
    inRect = (x >= dot.x && x <= dot.x + Xrange && y >= dot.y - Yrange && y <= dot.y );

    % 检测按键
    [keyIsDown, ~, keyCode] = KbCheck;
    if keyIsDown
        % 按空格键结束实验（当所有面孔都有圆点时）
        if keyCode(KbName('space')) && all(faceHasDot)
            experimentDone = true;
        % 按A键 - 红色圆点
        elseif keyCode(KbName('a')) && faceSelected
            dotColor = [255 0 0];
            currentDotColor = [255 0 0];
            villageSelected = true;
        % 按B键 - 黄色圆点
        elseif keyCode(KbName('b')) && faceSelected
            dotColor = [255 255 0];
            currentDotColor = [255 255 0];
            villageSelected = true;
        % 按C键 - 蓝色圆点
        elseif keyCode(KbName('c')) && faceSelected
            dotColor = [0 0 255];
            currentDotColor = [0 0 255];
            villageSelected = true;
        elseif keyCode(KbName('ESCAPE'))
            break;
        end
    end

    % --- 鼠标单击事件处理 (非阻塞) ---
    if mouseIsDown && ~mouseWasDown
        faceClicked = 0;
        for i = 1:numFaces
            if IsInRect(x, y, FRect(i,:))
                faceClicked = i;
                break;
            end
        end
        
        if faceClicked > 0
            % 点击了一个面孔
            if currentFace == faceClicked
                % 如果点击的是当前已选中的面孔，则清除它的点
                faceHasDot(faceClicked) = false;
                faceDotPositions(faceClicked, :) = [0, 0];
                village(faceClicked) = 0;
                faceBorderColors(faceClicked, :) = [128 128 128]; % 恢复灰色边框
            else
                % 否则，选择这个新面孔
                currentFace = faceClicked;
                faceSelected = true;
                % 重置为默认状态：灰色边框，未选择村庄
                dotColor = [128 128 128];
                currentDotColor = [128 128 128];
                villageSelected = false;
            end
        elseif inRect && faceSelected && villageSelected
            % 在矩形区域内点击，且已选择一个面孔，且已选择村庄
            faceDotPositions(currentFace, :) = [x, y];
            faceDotColors(currentFace, :) = dotColor;
            faceHasDot(currentFace) = true;
            
            % 根据dotColor设置边框为暗色版本
            dimFactor = 0.6; % 亮度因子
            faceBorderColors(currentFace, :) = dotColor * dimFactor;
            
            % 根据dotColor记录村庄信息
            if isequal(dotColor, [255 0 0])
                village(currentFace) = 1;
            elseif isequal(dotColor, [255 255 0])
                village(currentFace) = 2;
            elseif isequal(dotColor, [0 0 255])
                village(currentFace) = 3;
            end
        end
    end
    mouseWasDown = mouseIsDown; % 更新鼠标状态

    % 绘制开始
    Screen('FillRect', win, [0 0 0]); % 清空屏幕

    % 显示完成状态
    if all(faceHasDot)
        completionText = 'Complete! Press [space] to end.';
        DrawFormattedText(win, completionText, dot.x, dot.y+100, [0 255 0]);
    end

    % 中央分割线
    Screen('DrawLine', win, line.Color, ...
           line.Start(1), line.Start(2), line.End(1), line.End(2), line.Width);
    
    % 绘制面孔（带边框）
    for i = 1:numFaces
        if currentFace == i || faceHasDot(i)
            brightness = 1;
        else
            brightness = 0.5;
        end
        Screen('Drawtexture', win, Ftex{find(position==i)}, [], FRect(i,:), 0, [], brightness);
        
        % 绘制面孔边框
        if i == currentFace && faceSelected
            % 当前选中的面孔
            if faceHasDot(i)
                % 已经放置了点，显示暗色边框
                borderColor = faceBorderColors(i, :);
            else
                % 还没放置点
                if villageSelected
                    % 已选择村庄，显示对应村庄颜色
                    borderColor = currentDotColor;
                else
                    % 未选择村庄，显示灰色高亮
                    borderColor = [180 180 180];
                end
            end
        elseif faceHasDot(i)
            % 其他已放置点的面孔，显示暗色边框
            borderColor = faceBorderColors(i, :);
        else
            % 未选中且未放置点的面孔，黑色边框
            borderColor = [0 0 0];
        end
        Screen('FrameRect', win, borderColor, FRect(i,:), 3);
    end
    
    % 矩形
    % 计算矩形坐标 [left, top, right, bottom]
    penWidth = 3;       % 边框线宽
    rectColor = [225 225 225]; % 白色边框
    rect = [dot.x, dot.y - Yrange, ...
            dot.x + Xrange, dot.y];
    Screen('FrameRect', win, rectColor, rect, penWidth);

    % 绘制已放置的圆点
    for i = 1:numFaces
        if faceHasDot(i)
            Screen('DrawDots', win, faceDotPositions(i,:)', dotSize, faceDotColors(i,:), [], 2);
        end
    end
    
    % 如果已选择面孔且鼠标在矩形区域内，显示跟随鼠标的半透明圆点
    if faceSelected && inRect && ~faceHasDot(currentFace) && villageSelected
        previewColor = [dotColor, 150]; % 增加透明度
        Screen('DrawDots', win, [x; y], dotSize, previewColor, [], 2);
    end
        
    % % 显示当前状态信息
    % infoText = sprintf('Current Face: %d\nVillage: %s', ...
    %                   currentFace, mat2str(village));
    % % 选择合适的位置显示信息（例如屏幕左上角）
    % infoX = 50;
    % infoY = 50;
    % DrawFormattedText(win, infoText, infoX, infoY, [255 255 255]);

    Screen('Flip', win);
    
    % 短暂延迟，减少CPU占用
    WaitSecs(0.01);
end

if experimentDone
    result.F1X=((faceDotPositions(position(1),1)-dot.x)/Xrange)*100;
    result.F1Y=((dot.y-faceDotPositions(position(1),2))/Xrange)*100;
    result.F1V=village(position(1));
    result.F2X=((faceDotPositions(position(2),1)-dot.x)/Xrange)*100;
    result.F2Y=((dot.y-faceDotPositions(position(2),2))/Xrange)*100;
    result.F2V=village(position(2));
    result.F3X=((faceDotPositions(position(3),1)-dot.x)/Xrange)*100;
    result.F3Y=((dot.y-faceDotPositions(position(3),2))/Xrange)*100;
    result.F3V=village(position(3));
    result.F4X=((faceDotPositions(position(4),1)-dot.x)/Xrange)*100;
    result.F4Y=((dot.y-faceDotPositions(position(4),2))/Xrange)*100;
    result.F4V=village(position(4));
    result.F5X=((faceDotPositions(position(5),1)-dot.x)/Xrange)*100;
    result.F5Y=((dot.y-faceDotPositions(position(5),2))/Xrange)*100;
    result.F5V=village(position(5));
    result.F6X=((faceDotPositions(position(6),1)-dot.x)/Xrange)*100;
    result.F6Y=((dot.y-faceDotPositions(position(6),2))/Xrange)*100;
    result.F6V=village(position(6));
end

end
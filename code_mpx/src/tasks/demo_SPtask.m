function [result]=demo_SPtask(win,winRect,Ftex,Rect_SPtask,intro_tex,subinfo)
    mean_false=-1;
    mean_rt=99;
    exit=0;
    j=1;
    while mean_false~=0 || mean_rt>5
        if exit == 1
            break;
        end
        
        village=shuffle(1:3);
        
        for v=1:3
            if exit == 1
                break;
            end
            % 初始化试次变量
            correctSelections = 0;
            falseSelections = 0;
            selectedFaces = zeros(1, 6); % 记录哪些面孔已被选中
            triallist=[1:6; shuffle(1:6)]; %[face, position]
            if v ==1
                false = [];
                rt = [];
            end
            
            % 当前村庄的正确面孔
            correctFaces = [2*(village(v)-1)+1, 2*(village(v)-1)+2];
            
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
            
            Tsec = GetSecs();
            while correctSelections < 2
                % 检查ESC键
                exit=CheckEscKey();
                if exit==1
                    break;
                end
    
                % 随机顺序呈现面孔
                for i = 1:6
                    Screen('Drawtexture',win,Ftex{i},[],Rect_SPtask.face(triallist(2,i),:));
                    % 如果已经选择正确，绘制绿色边框
                    if selectedFaces(i) && ismember(i, correctFaces)
                        Screen('FrameRect', win, [0 255 0], Rect_SPtask.face(triallist(2,i),:), 3);
                    % 如果选择错误，绘制红色边框
                    elseif selectedFaces(i) && ~ismember(i, correctFaces)
                        Screen('FrameRect', win, [255 0 0], Rect_SPtask.face(triallist(2,i),:), 3);
                    end
                end

                %要求找全某村庄里的所有居民
                Screen('Drawtexture',win,intro_tex{village(v)},[],Rect_SPtask.intro);
                Screen('Flip', win);

                % 检测鼠标点击
                [x, y, buttons] = GetMouse(win);
            
                if any(buttons) % 如果鼠标被点击
                    % 检查点击了哪个面孔
                    for i = 1:6
                        faceRect = Rect_SPtask.face(triallist(2,i),:);
                        if IsInRect(x, y, faceRect)
                            % 如果这个面孔还没有被选择过
                            if ~selectedFaces(i)
                                selectedFaces(i) = true;
                                % 检查选择是否正确
                                if ismember(i, correctFaces)
                                    correctSelections = correctSelections + 1;
                                    if correctSelections == 2
                                        EndTsec = GetSecs();
                                    else
                                        EndTsec = 0;
                                    end
                                else
                                    falseSelections = falseSelections+1;
                                end
                            end
                            break;
                        end
                    end
                    
                    % 等待鼠标释放
                    while any(buttons)
                        [~, ~, buttons] = GetMouse(win);
                    end
                    WaitSecs(0.2); % 短暂的延迟防止多次点击
                end
            end
            
            % 单次试次结果
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
            result(3*(j-1)+v,1).SubNo = str2double(char(subinfo(1)));
            result(3*(j-1)+v,1).Name = char(subinfo(4));
            result(3*(j-1)+v,1).Gender = Gender;
            result(3*(j-1)+v,1).Age = str2double(char(subinfo(3)));
            result(3*(j-1)+v,1).Handedness = Handedness;

            rt(v) = EndTsec-Tsec;
            false(v) = falseSelections;
            result(3*(j-1)+v,1).village = village(v);
            result(3*(j-1)+v,1).face1 = correctFaces(1);
            result(3*(j-1)+v,1).face2 = correctFaces(2);
            result(3*(j-1)+v,1).false_time = false(v);
            result(3*(j-1)+v,1).rt = rt(v);
            result(3*(j-1)+v,1).mean_rt = mean(rt);
            result(3*(j-1)+v,1).mean_false = mean(false);
            result(3*(j-1)+v,1).block = j;
        end

        mean_rt = result(3*j,1).mean_rt;
        mean_false = result(3*j,1).mean_false;

        j = j+1;

    end
end

function exit = CheckEscKey()
    exit = 0;
    [keyIsDown, ~, keyCode] = KbCheck;
    if keyIsDown
        if keyCode(KbName('ESCAPE'))
            exit = 1;
        end
    end
end
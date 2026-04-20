function [fix,key,rgb,win,winRect,width,height,sizes,facevalue,FRect,line,dot]=load_MRpara()

%% 准备实验参数
    %  颜色
    rgb.black = [0,0,0];
    rgb.white = [255,255,255];
    
    fix = '+';
        
    % -------------------------------- for keyboard and mouse
    %     define key
    KbName('UnifyKeyNames');
    key.esc = KbName('ESCAPE');  % return key code
    key.space = KbName('SPACE'); 
    key.LeftArrow= KbName('LeftArrow');
    key.RightArrow = KbName('RightArrow');
    key.UpArrow = KbName('UpArrow');
    key.DownArrow = KbName('DownArrow');
    
    %  窗口
    %  测试 2 ，正式实验1
    AssertOpenGL;
    Screen('Preference', 'SkipSyncTests', 1);
    screenNumber = max(Screen('Screens'));
    [win, winRect] = Screen('OpenWindow', screenNumber,rgb.black);

    % rect=[0 0 1000 800];
    % [win, winRect] = Screen('OpenWindow', screenNumber,rgb.black,rect);

    width=winRect(3);
    height=winRect(4);

    topPriorityLevel = MaxPriority(win);
    [center_x,center_y] = RectCenter(winRect);
    
    
    %% 设置图片出现位置
    sizes.face=[0 0 200 201];
    for r = 0:1
        for c = 1:3
            if r==0
                FRect(r*3+c,:) = [center_x+(1/6)*width-400+300*(c-1) center_y-251 center_x+(1/6)*width-200+300*(c-1) center_y-50];
            elseif r==1
                FRect(r*3+c,:) = [center_x+(1/6)*width-400+300*(c-1) center_y+50 center_x+(1/6)*width-200+300*(c-1) center_y+251];
            end
        end
    end

    % 设置线条参数
    line.Color = [225 225 225]; % 白色线条
    line.Width = 3;       % 线条宽度（像素）
    lineLength = 800;    % 线条长度（像素）

    % 计算线条的起点和终点坐标
    line.Start = [center_x, center_y - lineLength/2];
    line.End = [center_x, center_y + lineLength/2];

    % 原点中心坐标
    dot.x = center_x - (3/8)*width;
    dot.y = center_y + lineLength/2;


    %% 化身坐标
        facevalue = [2.416, 4.788;
                 2.789, 7.765;
                 6.426, 8.527;
                 8.817, 6.716;
                 4.894, 2.020;
                 7.659, 3.185];
    facebar = round((facevalue/10) * 400);

end
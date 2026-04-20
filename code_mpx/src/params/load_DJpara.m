function [fix,key,rgb,win,winRect,width,height,sizes,Rect_DJtask] = load_DJpara()
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
    Rect_DJtask.face = [center_x-100 center_y-100 center_x+100 center_y+101];

end
function triallist = PDtask_trial()
%% 关键试次（中点中点）最基础组合
keytrial=[1	2 3	4;
        2 3	1 4;
        1 2	5 6;
        1 5	2 6;
        3 4	5 6;
        3 5	4 6;];

repeat_time = 2;
MM_task=zeros(30*repeat_time,1); % 是否执行中点的中点任务
for r=1:repeat_time
    % 顺序组合随机
    for i = 1:6
        o=randi([1,8]);
        if o == 1
            key_trial(6*(r-1)+i,:)=[keytrial(i,1) keytrial(i,2) keytrial(i,3) keytrial(i,4)];
        elseif o == 2
            key_trial(6*(r-1)+i,:)=[keytrial(i,1) keytrial(i,2) keytrial(i,4) keytrial(i,3)];
        elseif o == 3
            key_trial(6*(r-1)+i,:)=[keytrial(i,2) keytrial(i,1) keytrial(i,3) keytrial(i,4)];
        elseif o == 4
            key_trial(6*(r-1)+i,:)=[keytrial(i,2) keytrial(i,1) keytrial(i,4) keytrial(i,3)];
        elseif o == 5
            key_trial(6*(r-1)+i,:)=[keytrial(i,3) keytrial(i,4) keytrial(i,1) keytrial(i,2)];
        elseif o == 6
            key_trial(6*(r-1)+i,:)=[keytrial(i,3) keytrial(i,4) keytrial(i,2) keytrial(i,1)];
        elseif o == 7
            key_trial(6*(r-1)+i,:)=[keytrial(i,4) keytrial(i,3) keytrial(i,1) keytrial(i,2)];
        elseif o == 8
            key_trial(6*(r-1)+i,:)=[keytrial(i,4) keytrial(i,3) keytrial(i,2) keytrial(i,1)];
        end
    end
end

%% 补齐其他类型试次数
same_side=[2 3; 1 4; 1 5; 2 6; 3 5; 4 6];
diagonal = [1 3; 2 4; 1 6; 2 5; 3 6; 4 5];

for i = 1:repeat_time
    same_side_trial(6*(i-1)+1:6*i,:)=shuffle(same_side,1);
    diagonal_trial1(6*(i-1)+1:6*i,:)=shuffle(diagonal,1);
    diagonal_trial2(6*(i-1)+1:6*i,:)=shuffle(diagonal,1);
end

trial{1}=key_trial;
trial{2}=same_side_trial;
trial{3}=diagonal_trial1;
trial{4}=diagonal_trial2;

for i = 1:6*repeat_time
    order = shuffle(1:4);
    for t = 1:4
        if order(t) ~= 1
            trial{order(t)}(i,:)=shuffle(trial{order(t)}(i,:));
        end
    end
    triallist(i,:) = [trial{order(1)}(i,:) trial{order(2)}(i,:) trial{order(3)}(i,:) trial{order(4)}(i,:)];
end

triallist = shuffle(triallist,1);
triallist = reshape(triallist',2,[])';

for i = 2:size(triallist,1)
    ache = reshape(triallist(i-1:i,:)',[1 4]);
    for a = 1:6*repeat_time
        if MM_task(i)==0
            if isequal(key_trial(a,:),ache)
                MM_task(i-1:i,1)=[1;2];
                break
            end
        end
    end
end
for i=2:size(triallist,1)
    if isequal(MM_task(i-1:i,1),[0;0])
        if rand() < 0.25
            MM_task(i-1:i,1) = [1;2];
        else
            MM_task(i-1:i,1) = [0;0];
        end
    end
end

triallist(:,3)=MM_task; 

end